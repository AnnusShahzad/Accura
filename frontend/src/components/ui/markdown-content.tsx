"use client";

import {
  useMemo,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from "react";
import { useTheme } from "next-themes";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";

import { cn } from "@/lib/utils";

type MarkdownContentProps = {
  content: string;
  className?: string;
};

type MarkdownCodeProps = ComponentPropsWithoutRef<"code"> & {
  inline?: boolean;
  children?: ReactNode;
  isDark: boolean;
};

function normalizeMathMarkdown(input: string): string {
  let text = input;

  // Fix broken LaTeX line breaks like \[4pt] which should be \\[4pt].
  text = text.replace(
    /\\\[(\d+(?:\.\d+)?(?:pt|em|ex|mm|cm|in))\]/g,
    "\\\\[$1]"
  );

  // Support standard LaTeX delimiters in model output.
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, (_match, expr) => `$${expr}$`);
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, (_match, expr) => {
    return `\n$$\n${expr}\n$$\n`;
  });

  // Convert standalone bracket blocks containing LaTeX into display math.
  text = text.replace(/(^|\n)\s*\[\s*([\s\S]*?)\s*\]\s*(?=\n|$)/g, (match, lead, expr) => {
    if (/\]\(/.test(match)) return match;

    const looksLikeMath = /\\[a-zA-Z]+|[_^{}]/.test(expr);
    if (!looksLikeMath) return match;

    return `${lead}$$\n${expr}\n$$`;
  });

  // Convert inline parenthesized LaTeX snippets like ( \mathbf a ) to $\mathbf a$.
  text = text.replace(/\(\s*(\\[a-zA-Z][^\n()]{0,220})\s*\)/g, (_match, expr) => {
    return `$${expr}$`;
  });

  return text;
}

function MarkdownCode({ inline, className, children, isDark }: MarkdownCodeProps) {
  const [copied, setCopied] = useState(false);
  const text = String(children ?? "").replace(/\n$/, "");
  const match = /language-([\w-]+)/.exec(className || "");
  const language = match?.[1];

  if (inline || !language) {
    return (
      <code className="rounded bg-muted/50 px-1 py-0.5 font-medium text-[0.9em]">
        {children}
      </code>
    );
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="group relative my-6 overflow-hidden rounded-xl border bg-muted/20 shadow-sm">
      <div className="flex items-center justify-between border-b bg-muted/50 px-3 py-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {language}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="rounded-md border bg-background px-2.5 py-1 text-xs font-medium text-foreground/90 transition-colors hover:bg-muted"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={isDark ? oneDark : oneLight}
        customStyle={{
          margin: 0,
          padding: "1rem",
          background: "transparent",
          fontSize: "0.9rem",
          lineHeight: 1.65,
        }}
        codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
        showLineNumbers={text.split("\n").length > 5}
        wrapLongLines
      >
        {text}
      </SyntaxHighlighter>
    </div>
  );
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const normalizedContent = useMemo(() => normalizeMathMarkdown(content), [content]);

  return (
    <div
      className={cn(
        "prose max-w-none dark:prose-invert text-[15px] leading-7 sm:text-base sm:leading-8 prose-headings:scroll-mt-24 prose-headings:font-semibold prose-p:max-w-[78ch] prose-p:text-pretty prose-p:text-foreground/95 prose-strong:text-foreground prose-li:marker:text-muted-foreground prose-blockquote:text-foreground/85 prose-blockquote:border-l-primary/40 prose-code:before:content-none prose-code:after:content-none",
        className
      )}
    >
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => (
            <h1 className="mt-8 mb-4 text-2xl font-semibold tracking-tight sm:text-3xl">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-7 mb-3 text-xl font-semibold tracking-tight sm:text-2xl">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-6 mb-2 text-lg font-semibold tracking-tight sm:text-xl">
              {children}
            </h3>
          ),
          p: ({ children }) => <p className="my-4 leading-7">{children}</p>,
          ul: ({ children }) => (
            <ul className="my-4 list-disc space-y-2.5 pl-6">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-4 list-decimal space-y-2.5 pl-6">{children}</ol>
          ),
          li: ({ children }) => <li className="pl-1 leading-7">{children}</li>,
          input: ({ type, checked }) => {
            if (type !== "checkbox") return null;

            return (
              <input
                type="checkbox"
                checked={checked}
                readOnly
                disabled
                className="mr-2 size-4 rounded border-border accent-primary"
              />
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="my-5 border-l-4 bg-muted/30 py-1.5 pl-4 italic">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-8 border-border" />,
          a: ({ children, href }) => (
            <a
              className="font-medium text-primary underline underline-offset-4 transition-colors hover:text-primary/80"
              href={href}
              target="_blank"
              rel="noreferrer"
            >
              {children}
            </a>
          ),
          code: ({ className, children, ...props }) => (
            <MarkdownCode
              className={className}
              isDark={isDark}
              {...props}
            >
              {children}
            </MarkdownCode>
          ),
          table: ({ children }) => (
            <div className="my-7 w-full overflow-x-auto rounded-xl border bg-card shadow-sm">
              <table className="w-full min-w-[520px] border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b bg-muted/70 px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-foreground/90">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b px-3 py-2.5 align-top leading-6 text-foreground/90">
              {children}
            </td>
          ),
          img: ({ src, alt }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={src}
              alt={alt || "Markdown image"}
              className="my-6 rounded-xl border shadow-sm"
            />
          ),
        }}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}