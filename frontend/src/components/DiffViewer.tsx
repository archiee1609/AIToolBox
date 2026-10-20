import React, { useState } from 'react';
import { Copy, Check, FileDiff } from 'lucide-react';

interface DiffViewerProps {
  diff: string;
  filePath?: string;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({ diff, filePath }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(diff);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!diff) {
    return <div className="text-2xs text-dim italic p-3">No diff changes detected.</div>;
  }

  const lines = diff.split('\n');

  return (
    <div className="diff-container shadow-inner">
      <div
        className="px-3 py-1.5 border-b flex items-center justify-between text-2xs font-mono"
        style={{ backgroundColor: 'rgba(255, 255, 255, 0.03)', borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center gap-1.5 text-main font-semibold">
          <FileDiff size={13} className="text-indigo-400" />
          <span>{filePath || 'Unified Diff'}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-2xs text-muted hover:text-main transition"
        >
          {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
          <span>{copied ? 'Copied' : 'Copy Diff'}</span>
        </button>
      </div>

      <div className="p-2 overflow-x-auto max-h-80 select-text">
        {lines.map((line, idx) => {
          let lineStyle: React.CSSProperties = {
            padding: '1px 6px',
            borderRadius: '2px',
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            lineHeight: '1.45',
            display: 'block'
          };

          if (line.startsWith('+') && !line.startsWith('+++')) {
            lineStyle.backgroundColor = 'rgba(16, 185, 129, 0.12)';
            lineStyle.color = '#34d399';
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            lineStyle.backgroundColor = 'rgba(239, 68, 68, 0.12)';
            lineStyle.color = '#f87171';
          } else if (line.startsWith('@@')) {
            lineStyle.backgroundColor = 'rgba(99, 102, 241, 0.12)';
            lineStyle.color = '#818cf8';
            lineStyle.fontWeight = 600;
          } else {
            lineStyle.color = 'var(--text-muted)';
          }

          return (
            <div key={idx} style={lineStyle}>
              {line || ' '}
            </div>
          );
        })}
      </div>
    </div>
  );
};
