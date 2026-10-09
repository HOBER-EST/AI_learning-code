import type { ReactNode } from "react";
import type { HeapObject, Value } from "../types";

export interface HeapContext {
  heap: Record<string, HeapObject>;
  claimedBy: Map<string, string>;
}

/** A value in a frame or object slot: inline primitive, or a pointer dot. */
export function ValueView({ value, highlight = false }: { value: Value; highlight?: boolean }) {
  if (value.t === "prim") return <span className="prim">{value.v}</span>;
  if (value.t === "empty") return <span className="link-empty">∅</span>;
  return <span className="ptr" data-ref={value.id} data-hl={highlight ? "1" : undefined} title="指向一个对象" />;
}

function Labeled({ id, type, children }: { id: string; type: ReactNode; children: ReactNode }) {
  return (
    <div className="obj" data-obj-id={id}>
      <div className="obj-type">{type}</div>
      {children}
    </div>
  );
}

function AttrTable({ attrs }: { attrs: [string, Value][] }) {
  if (!attrs.length) return <div className="seq-empty">（无属性）</div>;
  return (
    <table className="kv">
      <tbody>
        {attrs.map(([name, v]) => (
          <tr key={name}>
            <td className="key">{name}</td>
            <td>
              <ValueView value={v} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function ObjectView({ id, ctx }: { id: string; ctx: HeapContext }) {
  const obj = ctx.heap[id];
  if (!obj) return null;
  switch (obj.t) {
    case "list":
    case "tuple":
    case "set":
      return (
        <Labeled id={id} type={obj.len > obj.items.length ? `${obj.t}（显示前 ${obj.items.length} / ${obj.len} 项）` : obj.t}>
          <div className={`seq ${obj.t}`}>
            {obj.items.length === 0 && <div className="seq-empty">空</div>}
            {obj.items.map((v, i) => (
              <div className="seq-cell" key={i}>
                <span className="idx">{obj.t === "set" ? "" : i}</span>
                <ValueView value={v} />
              </div>
            ))}
          </div>
        </Labeled>
      );
    case "dict":
      return (
        <Labeled id={id} type="dict">
          <table className="kv">
            <tbody>
              {obj.items.length === 0 && (
                <tr>
                  <td className="key">空</td>
                </tr>
              )}
              {obj.items.map(([k, v], i) => (
                <tr key={i}>
                  <td className="key">
                    <ValueView value={k} />
                  </td>
                  <td>
                    <ValueView value={v} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Labeled>
      );
    case "func":
      return (
        <div className="obj func-obj" data-obj-id={id}>
          <span className="kw">{obj.builtin ? "builtin " : "func "}</span>
          {obj.name}
          {obj.params}
          {obj.line ? <span className="kw"> &lt;line {obj.line}&gt;</span> : null}
          {obj.parent ? <span className="kw"> [parent={obj.parent}]</span> : null}
        </div>
      );
    case "method":
      return (
        <Labeled id={id} type="bound method">
          <AttrTable
            attrs={[
              ["__func__", obj.func],
              ["__self__", obj.self],
            ]}
          />
        </Labeled>
      );
    case "class":
      return (
        <Labeled id={id} type={`class ${obj.name}${obj.bases.length ? `(${obj.bases.join(", ")})` : ""}`}>
          <AttrTable attrs={obj.attrs} />
        </Labeled>
      );
    case "instance":
      return (
        <Labeled id={id} type={`${obj.cls} 实例`}>
          <AttrTable attrs={obj.attrs} />
        </Labeled>
      );
    case "link":
      return <LinkChain id={id} ctx={ctx} />;
    case "tree":
      return (
        <div className="obj tree-root">
          <div className="obj-type">Tree</div>
          <TreeNodeView id={id} ctx={ctx} />
        </div>
      );
    default:
      return (
        <div className="obj" data-obj-id={id}>
          <div className="seq">
            <div className="seq-cell">{obj.repr}</div>
          </div>
        </div>
      );
  }
}

function LinkChain({ id, ctx }: { id: string; ctx: HeapContext }) {
  const nodes: string[] = [id];
  let cur = id;
  for (;;) {
    const obj = ctx.heap[cur];
    if (obj?.t !== "link" || obj.rest.t !== "ref" || ctx.claimedBy.get(obj.rest.id) !== cur) break;
    cur = obj.rest.id;
    nodes.push(cur);
  }
  return (
    <div className="obj">
      <div className="obj-type">Link</div>
      <div className="link-chain">
        {nodes.map((nid) => {
          const node = ctx.heap[nid] as Extract<HeapObject, { t: "link" }>;
          return (
            <div className="link-node" data-obj-id={nid} key={nid}>
              <div>
                <span className="field">first</span>
                <ValueView value={node.first} />
              </div>
              <div>
                <span className="field">rest</span>
                <ValueView value={node.rest} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TreeNodeView({ id, ctx }: { id: string; ctx: HeapContext }) {
  const node = ctx.heap[id] as Extract<HeapObject, { t: "tree" }>;
  const inline = node.branches.filter((b) => b.t === "ref" && ctx.claimedBy.get(b.id) === id) as { t: "ref"; id: string }[];
  const pointers = node.branches.filter((b) => !(b.t === "ref" && ctx.claimedBy.get(b.id) === id));
  return (
    <div className="tree-node-wrap">
      <div className="tree-node" data-obj-id={id}>
        <ValueView value={node.label} />
        {pointers.map((b, i) => (
          <ValueView key={i} value={b} />
        ))}
      </div>
      {inline.length > 0 && (
        <div className="tree-children">
          {inline.map((b) => (
            <TreeNodeView key={b.id} id={b.id} ctx={ctx} />
          ))}
        </div>
      )}
    </div>
  );
}
