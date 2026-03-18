/**
 * Site header with keyboard-navigable primary navigation.
 *
 * Accessibility:
 * - <header> is a landmark (role="banner") — screen readers can jump to it.
 * - <nav> with aria-label distinguishes from other <nav> elements on the page.
 * - Current page link has aria-current="page".
 * - Logo link always announces the site name, not just "logo".
 * - No hamburger menu that requires JavaScript; links are always visible.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';

export default function SiteHeader(): React.ReactElement {
  return (
    <header
      style={{
        background: '#16213e',
        borderBottom: '2px solid #60a5fa',
        padding: '0 1.5rem',
      }}
    >
      <div
        style={{
          maxWidth: '900px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          minHeight: '60px',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        {/* Site identity */}
        <NavLink
          to="/"
          style={{
            color: '#e2e8f0',
            fontWeight: 700,
            fontSize: '1.25rem',
            textDecoration: 'none',
          }}
          aria-label="Blind Assistant Learning — home"
        >
          Blind Assistant Learning
        </NavLink>

        {/* Primary navigation */}
        <nav aria-label="Primary navigation">
          <ul
            style={{
              display: 'flex',
              gap: '1.5rem',
              listStyle: 'none',
              margin: 0,
              padding: 0,
            }}
            role="list"
          >
            <li>
              <NavLink
                to="/"
                end
                aria-current={({ isActive }) => (isActive ? 'page' : undefined)}
                style={({ isActive }) => ({
                  color: isActive ? '#93c5fd' : '#60a5fa',
                  fontWeight: isActive ? 700 : 400,
                  textDecoration: 'underline',
                })}
              >
                Courses
              </NavLink>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
