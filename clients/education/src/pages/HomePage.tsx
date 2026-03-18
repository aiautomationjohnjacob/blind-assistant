/**
 * Home page — course catalogue.
 *
 * Accessibility:
 * - Page <h1> is the first heading; focus moves here on route change
 *   (App.tsx sets tabIndex={-1} on <main>; RouteAnnouncer in App will handle focus).
 * - Course list is a plain <ul>/<li> + article structure, not a div-soup,
 *   so NVDA's list navigation (L key) works correctly.
 * - Loading state is announced via aria-live="polite".
 */

import React, { useEffect, useRef } from 'react';
import CourseCard, { Course } from '../components/CourseCard';

// Placeholder courses — replaced by API fetch in production.
const SAMPLE_COURSES: Course[] = [
  {
    id: 'getting-started',
    title: 'Getting Started with Blind Assistant',
    description:
      'Learn how to set up the app, configure your voice preferences, and complete your first task entirely by voice.',
    lessonCount: 5,
    completedLessons: 0,
    durationMinutes: 20,
  },
  {
    id: 'second-brain',
    title: 'Your Second Brain — Voice Notes and Memory',
    description:
      'Add notes, reminders, and personal knowledge by speaking naturally. Search and retrieve everything by voice.',
    lessonCount: 4,
    completedLessons: 0,
    durationMinutes: 15,
  },
  {
    id: 'ordering-food',
    title: 'Ordering Food and Groceries',
    description:
      'Place orders at any restaurant or grocery service entirely by voice. Includes the financial risk disclosure flow.',
    lessonCount: 6,
    completedLessons: 0,
    durationMinutes: 25,
  },
  {
    id: 'screen-description',
    title: 'Describing Your Screen',
    description:
      'Ask the assistant to describe any app, image, or document on your screen — even inaccessible apps.',
    lessonCount: 3,
    completedLessons: 0,
    durationMinutes: 12,
  },
];

export default function HomePage(): React.ReactElement {
  const headingRef = useRef<HTMLHeadingElement>(null);

  // Move focus to h1 on mount so NVDA announces the page on route change.
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
      <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
        Courses
      </h1>
      <p style={{ color: '#94a3b8', marginBottom: '2rem' }}>
        All courses are audio-primary and fully completable by keyboard with no mouse.
        Press <kbd>H</kbd> in NVDA or VoiceOver to jump between course headings.
      </p>

      <ul
        style={{ listStyle: 'none', padding: 0, margin: 0 }}
        role="list"
        aria-label="Available courses"
      >
        {SAMPLE_COURSES.map((course) => (
          <li key={course.id}>
            <CourseCard course={course} />
          </li>
        ))}
      </ul>
    </>
  );
}
