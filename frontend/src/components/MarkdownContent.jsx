import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function MarkdownContent({ children }) {
  return (
    <div className="prose-article">
      <Markdown remarkPlugins={[remarkGfm]} skipHtml>
        {children || ""}
      </Markdown>
    </div>
  );
}
