import React, { useState } from 'react';
import { marked } from 'marked';
import { Copy, Check } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  // If the content is simple text, marked parses it into clean HTML.
  const rawHtml = React.useMemo(() => {
    try {
      return marked.parse(content, { breaks: true, gfm: true }) as string;
    } catch {
      return content;
    }
  }, [content]);

  return (
    <div
      className="markdown-body select-text"
      dangerouslySetInnerHTML={{ __html: rawHtml }}
    />
  );
};
