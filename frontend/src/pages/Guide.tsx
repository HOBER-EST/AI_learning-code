import usage from "../../../docs/USAGE.md?raw";
import { Markdown } from "../components/Markdown";

export function Guide() {
  return (
    <div className="page">
      <div className="card card-body guide">
        <Markdown>{usage}</Markdown>
      </div>
    </div>
  );
}
