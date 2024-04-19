from typing import Optional, List, Dict
import pickle
import os
from glob import glob
import shutil
from loguru import logger
from tqdm import tqdm

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Table, CompositeElement
from langchain_core.documents import Document

from app.backend.splitters import PDFSplitter
from app.backend.chains.docqa import ImageCaptioningChain, CaptionFilterChain

from app.backend.utils import get_rand_str, encode_image, compute_file_digest


class MultiModalPDFSplitter(PDFSplitter):
    def __init__(
        self,
        work_dir: str,
        max_chunk_size: int,
        min_chunk_size: int,
        extract_images: bool = False,
        filter_captions: bool = True,
        force_new: bool = False,
    ) -> None:

        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.extract_images = extract_images
        self.work_dir = work_dir
        self.force_new = force_new

        self.filter_captions = filter_captions

    def split(self, file_path: str) -> List[Document]:
        file_digest = compute_file_digest(file_path)

        file_work_dir = os.path.join(self.work_dir, file_digest)
        elements_file = os.path.join(file_work_dir, "elements.pkl")

        # Backup existing data before overwriting them
        if os.path.exists(elements_file) and self.force_new:
            file_work_dir_backup = os.path.join(
                self.work_dir,
                "backup",
                file_digest,
                get_rand_str(n=6).lower(),
            )
            shutil.move(file_work_dir, file_work_dir_backup)
            logger.info(f"Moved existing files to {file_work_dir_backup}")

        os.makedirs(file_work_dir, exist_ok=True)

        if self.extract_images:
            images_folder = os.path.join(file_work_dir, "images")
            captions_folder = os.path.join(file_work_dir, "captions")
            os.makedirs(images_folder, exist_ok=True)
            os.makedirs(captions_folder, exist_ok=True)
        else:
            images_folder = False

        if os.path.exists(elements_file):
            logger.info(f"Found pre-computed pdf elements")
            with open(elements_file, "rb") as f:
                pdf_elements = pickle.load(f)
        else:
            logger.info(f"Extracting elements from pdf with Unstructured...")
            pdf_elements = partition_pdf(
                strategy="hi_res",
                hi_res_model_name="yolox_quantized",
                filename=file_path,
                extract_images_in_pdf=self.extract_images,
                extract_image_block_types=["Image", "Picture", "Figure"],
                extract_image_block_to_payload=False,
                infer_table_structure=True,
                chunking_strategy="by_title",
                multipage_sections=False,
                # Chunking params to aggregate text blocks
                # Attempt to create a new chunk 3800 chars
                # Attempt to keep chunks > 2000 chars
                max_characters=self.max_chunk_size,
                combine_text_under_n_chars=self.min_chunk_size,
                extract_image_block_output_dir=images_folder,
            )

            with open(elements_file, "wb") as f:
                pickle.dump(pdf_elements, f)

        logger.info(f"Found {len(pdf_elements)} elements in the pdf.")

        docs = []
        for element in pdf_elements:

            if isinstance(element, Table):
                doc_type = "table"
            elif isinstance(element, CompositeElement):
                doc_type = "text"
            else:
                logger.error(f"Element {type(element)} not supported!")
                raise NotImplementedError

            docs.append(
                Document(
                    page_content=element.text,
                    metadata={
                        "doc_type": doc_type,
                        "page": element.metadata.page_number,
                        "source_id": file_digest,
                    },
                )
            )

        if self.extract_images:
            images_with_captions = self.caption_images(
                images_folder=images_folder, captions_folder=captions_folder
            )

            filtered_images_file = os.path.join(file_work_dir, "filtered_images.pkl")
            if self.filter_captions:
                if os.path.exists(filtered_images_file):
                    with open(filtered_images_file, "rb") as f:
                        images_list = pickle.load(f)

                    images_list = [os.path.basename(i) for i in images_list]
                    images_with_captions = {
                        k: v
                        for k, v in images_with_captions.items()
                        if os.path.basename(k) in images_list
                    }
                    logger.info(
                        f"Loaded list of captions to keep {len(images_with_captions)}"
                    )
                else:
                    images_with_captions = self.filter_images_from_their_caption(
                        images_with_captions
                    )
                    with open(filtered_images_file, "wb") as f:
                        pickle.dump(list(images_with_captions.keys()), f)

            for file, caption in images_with_captions.items():
                docs.append(
                    Document(
                        page_content=caption,
                        metadata={
                            "doc_type": "image",
                            "page": int(
                                os.path.basename(file).split(".")[0].split("-")[1]
                            ),
                            "source_id": file_digest,  # doc file
                            "image_file": file,  # single image extracted from the doc
                        },
                    )
                )

        return docs

    @staticmethod
    def caption_images(images_folder: str, captions_folder: str) -> Dict[str, str]:
        captioning_chain = ImageCaptioningChain()

        images_with_captions = {}
        logger.info(f"Generating/loading image captions...")
        for image_file in tqdm(glob(os.path.join(images_folder, "*.jpg"))):
            caption_file = os.path.join(
                captions_folder, os.path.basename(image_file).split(".")[0] + ".txt"
            )

            # Backup/load pre-computed captions since they are relatively expensive
            if os.path.exists(caption_file):
                with open(caption_file, "r") as f:
                    caption = f.read()
            else:
                image_b64 = encode_image(image_file)
                logger.debug(
                    f"Computing caption with GPT-4V for image {os.path.basename(image_file)}"
                )
                caption = captioning_chain.run(image_b64=image_b64)
                with open(caption_file, "w") as f:
                    f.write(caption)

            images_with_captions[image_file] = caption

        return images_with_captions

    @staticmethod
    def filter_images_from_their_caption(
        images_with_captions: Dict[str, str]
    ) -> Dict[str, str]:
        filter_chain = CaptionFilterChain()

        filtered_captions = {}
        logger.info(f"Filtering out irrelevant images based on their captions...")
        for k, v in tqdm(images_with_captions.items()):
            if filter_chain.run(caption=v):
                filtered_captions[k] = v
        logger.info(
            f"{len(filtered_captions)} images have been kept out of {len(images_with_captions)}."
        )
        return filtered_captions


if __name__ == "__main__":
    pdf_doc = "data/documents/swda_factsheet.pdf"

    chunker = MultiModalPDFSplitter(
        work_dir="data/test/splitters_cache",
        max_chunk_size=3000,
        min_chunk_size=0,
        extract_images=False,
        filter_captions=True,
        force_new=True,
    )

    docs = chunker.split(file_path=pdf_doc)

    # MultiModalPDFSplitter.pretty_print_chunks(chunks=docs, file="chunks.txt")
