import type { ArtifactPreview } from "../api/types";

type Props = {
  preview: ArtifactPreview;
  onClose: () => void;
};

export function ArtifactPreviewPanel({ preview, onClose }: Props) {
  return (
    <section className="artifact-preview" aria-label="Artifact preview">
      <header>
        <div>
          <strong>{preview.relative_path}</strong>
          <small>
            {preview.returned_bytes} / {preview.total_size_bytes} bytes
            {preview.truncated ? " · truncated" : ""}
          </small>
        </div>
        <button type="button" onClick={onClose}>Close</button>
      </header>

      {/* React 会转义字符串；不要改成 dangerouslySetInnerHTML。 */}
      <pre>{preview.content}</pre>
    </section>
  );
}
