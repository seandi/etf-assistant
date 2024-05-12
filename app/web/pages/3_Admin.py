import streamlit as st
import dotenv
import os
from functools import partial


from app.web.storage.docs_db import ETFDocumentsDatabase, DocMetadata
from app.web.storage.docs_storage import ETFDocStorage
from app.web.utils import load_etf_db

dotenv.load_dotenv(override=True)
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    " <style> div[class^='block-container'] { padding-top: 2rem; } </style> ",
    unsafe_allow_html=True,
)

docs_db = ETFDocumentsDatabase(db_path=os.environ.get("DOC_DB"))
docs_storage = ETFDocStorage()
docs = docs_db.get_docs()
etf_df = load_etf_db()


manage_tab, upload_tab = st.tabs(["Manage Documents", "New Document"])


with manage_tab:
    cmanage, clist = st.columns([0.5, 0.5])

    with clist:
        st.subheader("Existing documents")
        st.dataframe(
            docs,
            hide_index=True,
            column_order=[
                "id",
                "name",
                "bucket_filename",
                "vectorstore_id",
                "top_k",
                "filter_sources",
            ],
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "name": st.column_config.Column("Name"),
                "bucket_filename": st.column_config.Column("Bucket"),
                "vectorstore_id": st.column_config.Column("Vectorstore ID"),
                "top_k": st.column_config.NumberColumn("LLM Chunks"),
                "filter_sources": st.column_config.CheckboxColumn("Filter Sources"),
            },
        )

    with cmanage:
        st.subheader("Manage document")

        st.write("")
        selected_option = st.selectbox(
            placeholder="Select a document to manage",
            label="select_doc_to_manage",
            options=[str(d.id) + " - " + d.name for d in docs],
            index=None,
            label_visibility="collapsed",
        )
        if selected_option is not None:
            selected_doc: DocMetadata = [
                d for d in docs if d.id == int(selected_option.split(" - ")[0])
            ][0]
            st.subheader(selected_doc.name)
            if selected_doc.description is not None:
                st.write(selected_doc.description)

            c1, c2 = st.columns([0.7, 0.3])

            assigned_etfs_manage = c1.multiselect(
                "select_eft_to_add",
                options=etf_df["name"] + " - " + etf_df["isin"],
                label_visibility="collapsed",
                placeholder="Choose an ETF",
            )
            if c2.button("Assign to these ETFs", use_container_width=True):
                if len(assigned_etfs_manage) > 0:
                    assigned_etfs_manage = [
                        e.split(" - ")[1] for e in assigned_etfs_manage
                    ]
                for isin in assigned_etfs_manage:
                    docs_db.assign_doc_to_etf(doc_id=selected_doc.id, etf_isin=isin)

            assigned_etfs = docs_db.get_doc_etfs(doc_id=selected_doc.id)
            with st.expander(label=f"Assigned to {len(assigned_etfs)} ETFs"):
                if len(assigned_etfs) == 0:
                    st.write("This document has not been assigned to any ETF yet.")
                for isin in assigned_etfs:
                    cc1, cc2 = st.columns(2)
                    cc1.write(isin)
                    cc2.button(
                        "Remove",
                        key=f"remove_{isin}",
                        on_click=partial(
                            docs_db.unassign_doc, doc_id=selected_doc.id, etf_isin=isin
                        ),
                    )

            if st.button("Delete", use_container_width=True):
                docs_db.delete_doc(doc_id=selected_doc.id)
                st.rerun()


with upload_tab:
    r1, r2 = st.columns(2)

    with r1:
        doc_name = st.text_input(
            label="Short name:", key="doc_name_input", max_chars=20
        )
        doc_description = st.text_area(
            label="Document description:", key="doc_descr_input", max_chars=500
        )

        assigned_etfs_upload = st.multiselect(
            "Select to which ETFs this document should be assigned:",
            options=etf_df["name"] + " - " + etf_df["isin"],
        )

    with r2:
        splitting_strategy = st.radio(
            label="Document splitting strategy:",
            options=["By page", " By layout"],
            key="doc_splitting_startegy",
        )
        multimodal = st.checkbox("Include images", value=False)
        filter_sources = st.checkbox("Filter sources", value=False)

        top_k = st.number_input(
            label="Chunks passed to LLM:",
            min_value=2,
            max_value=10,
            key="top_k",
        )

        data = st.file_uploader("Upload new document", key="doc_upload")

    add_button = st.button(
        "Add",
        use_container_width=True,
        key="add",
    )

    if add_button:
        if data is None or len(doc_name) == 0:
            st.error("You must provide a name and load the document first!")
        elif "-" in doc_name:
            st.error(f"Document name must not contain the symbol '-'")
        else:
            with st.spinner("Processing the document..."):
                if len(assigned_etfs_upload) > 0:
                    assigned_etfs_upload = [
                        e.split(" - ")[1] for e in assigned_etfs_upload
                    ]
                res = docs_storage.add_document(
                    data=data,
                    name=doc_name,
                    description=doc_description,
                    split_by=splitting_strategy.lower().replace(" ", ""),
                    multimodal=multimodal,
                    top_k=top_k,
                    filter_sources=filter_sources,
                    assigned_etfs=assigned_etfs_upload,
                )
            if res:
                st.success("Document added!")
            else:
                st.error("Failed to add docuement")
            st.rerun()
