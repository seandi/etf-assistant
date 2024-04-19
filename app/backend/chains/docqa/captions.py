from langchain.prompts import PromptTemplate
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

CAPTION_FILTER_PROMPT_TEMPLATE = """Given the following caption of an image, return YES if the caption is about a graph, a plot or a scale and NO if it isn't.
In particular you should return NO if the image is a logo, a title or a header.

> Image Caption: {caption}
> Relevant (YES / NO):"""


class CaptionFilterChain:
    def __init__(self) -> None:

        self.chain = (
            PromptTemplate.from_template(CAPTION_FILTER_PROMPT_TEMPLATE)
            | ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
            | BooleanOutputParser()
        )

    def run(self, caption: str) -> bool:
        return self.chain.invoke({"caption": caption})


class ImageCaptioningChain:
    def __init__(self) -> None:
        self.prompt = (
            "Describe the image in detail. Be specific about graphs, such as bar plots."
        )

        self.chain = (
            ChatOpenAI(model="gpt-4-vision-preview", max_tokens=1024)
            | StrOutputParser()
        )

    def run(self, image_b64: str, langfuse_handler=None):
        config = {}
        if langfuse_handler is not None:
            config["callbacks"] = [langfuse_handler]

        return self.chain.invoke(
            [
                HumanMessage(
                    content=[
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ]
                )
            ],
            config=config,
        )


if __name__ == "__main__":
    chain = CaptionFilterChain()

    caption1 = """
    This image is a wide, horizontal line graph with a pale yellow line plotting data across a timeline. The x-axis represents time, beginning at "Sep-09" and ending at "Jan-24," suggesting a range from September 2009 to January 2024. The time intervals are marked at two-year increments, each labeled with "Sep" followed by the last two digits of the year. The y-axis is on the left side and it's not clearly labeled, but there are three horizontal lines that likely represent different values; however, the values are not readable as they are cut off at the top ("0,000"). The graph line itself starts at the lower left part of the graph, gradually rises over time, and becomes more volatile towards the right side, with larger ups and downs, especially after "Sep-19."

    The background of the graph is white, the axis lines are grey, and the line of the graph is a thick, bright yellow. The line's thickness varies slightly, indicating that it might represent some range of values or confidence intervals rather than a single precise measurement line. There's no title or legend provided, so the specific context or data represented by the graph is unknown."""

    caption2 = """The image displays a logo consisting of two elements of text. The upper and larger text reads "iShares" in a bold, sans-serif font. Just beneath it, in smaller lettering, is the text "by BlackRock". The font of the lower text is also sans-serif but is lighter and less prominent compared to the "iShares" text. Both texts are aligned to the left and there is a registered trademark symbol (®) at the end of "iShares". The color scheme of the logo is monochromatic, with black text on a white background. There are no graphs, images, or other graphical elements in the image—it is strictly typographic."""

    res = chain.chain.invoke({"caption": caption1})
    print(res)

    res = chain.chain.invoke({"caption": caption2})
    print(res)
