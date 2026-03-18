/**
 * 404 Not Found page.
 *
 * Accessibility: focus moves to the <h1> on mount so screen readers announce
 * the error immediately.
 */

import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

export default function NotFoundPage(): React.ReactElement {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
      <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
        Page not found
      </h1>
      <p>The page you requested does not exist.</p>
      <Link to="/" className="btn">
        Return to course catalogue
      </Link>
    </>
  );
}
