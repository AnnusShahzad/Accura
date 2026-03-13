"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Expand } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type ResponseViewerProps = {
  content: string;
  title?: string;
  className?: string;
  previewHeight?: number;
};

export function ResponseViewer({
  content,
  title = "Response",
  className,
  previewHeight = 320,
}: ResponseViewerProps) {
  const [expanded, setExpanded] = useState(false);

  const shouldCollapse = useMemo(() => {
    const lineCount = content.split("\n").length;
    return content.length > 900 || lineCount > 18;
  }, [content]);

  const wordCount = useMemo(() => {
    return content.trim().split(/\s+/).filter(Boolean).length;
  }, [content]);

  const readTime = Math.max(1, Math.ceil(wordCount / 220));

  return (
    <div
      className={cn(
        "rounded-2xl border border-border/70 bg-gradient-to-b from-background to-muted/20 p-4 shadow-sm sm:p-6",
        className
      )}
    >
      <div
        className={cn(
          "relative transition-[max-height] duration-300 ease-in-out",
          shouldCollapse && !expanded && "overflow-hidden"
        )}
        style={
          shouldCollapse && !expanded ? { maxHeight: `${previewHeight}px` } : undefined
        }
      >
        <MarkdownContent content={content} />

        {shouldCollapse && !expanded && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-background via-background/95 to-transparent" />
        )}
      </div>

      {shouldCollapse && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-border/60 pt-4">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? (
              <ChevronUp className="mr-1.5 h-4 w-4" />
            ) : (
              <ChevronDown className="mr-1.5 h-4 w-4" />
            )}
            {expanded ? "Collapse" : "Expand Inline"}
          </Button>

          <Dialog>
            <DialogTrigger asChild>
              <Button type="button" size="sm">
                <Expand className="mr-1.5 h-4 w-4" />
                Open Reader
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90vh] gap-0 overflow-hidden p-0 sm:max-w-5xl">
              <DialogHeader className="border-b px-5 py-4 sm:px-6">
                <DialogTitle className="text-base sm:text-lg">{title}</DialogTitle>
                <DialogDescription>
                  {wordCount.toLocaleString()} words • {readTime} min read
                </DialogDescription>
              </DialogHeader>
              <ScrollArea className="h-[78vh]">
                <div className="px-5 py-6 sm:px-8">
                  <MarkdownContent content={content} />
                </div>
              </ScrollArea>
            </DialogContent>
          </Dialog>
        </div>
      )}
    </div>
  );
}