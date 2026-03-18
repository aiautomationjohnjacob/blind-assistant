/**
 * Site footer with copyright and legal links.
 *
 * Accessibility:
 * - <footer> is a landmark (role="contentinfo") — screen readers can jump past it.
 * - All links are underlined (not colour-only).
 */

import React from 'react';

export default function SiteFooter(): React.ReactElement {
  return (
    <footer
      role="contentinfo"
      style={{
        background: '#16213e',
        borderTop: '1px solid #334155',
        padding: '1.5rem',
        marginTop: '3rem',
        textAlign: 'center',
        color: '#94a3b8',
        fontSize: '0.9rem',
      }}
    >
      <p>
        &copy; {new Date().getFullYear()} Blind Assistant — a nonprofit initiative.{' '}
        <a href="https://blind-assistant.org" style={{ color: '#60a5fa' }}>
          Main site
        </a>
      </p>
      <p>
        This platform is{' '}
        <a
          href="https://github.com/aiautomationjohnjacob/blind-assistant"
          style={{ color: '#60a5fa' }}
        >
          open source
        </a>
        . Contributions from blind users and developers are welcome.
      </p>
    </footer>
  );
}
