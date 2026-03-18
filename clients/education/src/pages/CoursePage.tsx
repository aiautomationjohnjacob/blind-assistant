/**
 * Course detail page — shows lesson list for a course.
 *
 * Accessibility:
 * - Lesson list uses ordered <ol>/<li> to convey sequence.
 * - Each lesson link includes the lesson number and title.
 * - Completed lessons are marked with aria-label addition ("completed").
 * - Focus moves to <h1> on mount.
 */

import React, { useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';

interface Lesson {
  id: string;
  title: string;
  durationMinutes: number;
  completed: boolean;
}

// Placeholder lessons — replaced by API fetch in production.
const COURSE_DATA: Record<string, { title: string; lessons: Lesson[] }> = {
  'getting-started': {
    title: 'Getting Started with Blind Assistant',
    lessons: [
      { id: 'gs-1', title: 'Welcome and overview', durationMinutes: 3, completed: false },
      { id: 'gs-2', title: 'Installing the app', durationMinutes: 5, completed: false },
      { id: 'gs-3', title: 'Setting your voice preferences', durationMinutes: 4, completed: false },
      { id: 'gs-4', title: 'Your first voice command', durationMinutes: 4, completed: false },
      { id: 'gs-5', title: 'Getting help and troubleshooting', durationMinutes: 4, completed: false },
    ],
  },
  'second-brain': {
    title: 'Your Second Brain — Voice Notes and Memory',
    lessons: [
      { id: 'sb-1', title: 'What is a Second Brain?', durationMinutes: 3, completed: false },
      { id: 'sb-2', title: 'Adding your first voice note', durationMinutes: 4, completed: false },
      { id: 'sb-3', title: 'Searching and retrieving notes', durationMinutes: 4, completed: false },
      { id: 'sb-4', title: 'Organising by topic and date', durationMinutes: 4, completed: false },
    ],
  },
  'ordering-food': {
    title: 'Ordering Food and Groceries',
    lessons: [
      { id: 'of-1', title: 'Introduction to voice ordering', durationMinutes: 3, completed: false },
      { id: 'of-2', title: 'Choosing a restaurant', durationMinutes: 4, completed: false },
      { id: 'of-3', title: 'Picking items from the menu', durationMinutes: 5, completed: false },
      { id: 'of-4', title: 'The financial risk disclosure', durationMinutes: 4, completed: false },
      { id: 'of-5', title: 'Confirming and placing your order', durationMinutes: 5, completed: false },
      { id: 'of-6', title: 'Tracking your delivery', durationMinutes: 4, completed: false },
    ],
  },
  'screen-description': {
    title: 'Describing Your Screen',
    lessons: [
      { id: 'sd-1', title: 'How screen description works', durationMinutes: 4, completed: false },
      { id: 'sd-2', title: 'Describing images and documents', durationMinutes: 4, completed: false },
      { id: 'sd-3', title: 'Navigating inaccessible apps', durationMinutes: 4, completed: false },
    ],
  },
};

export default function CoursePage(): React.ReactElement {
  const { courseId } = useParams<{ courseId: string }>();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, [courseId]);

  const data = courseId ? COURSE_DATA[courseId] : null;

  if (!data) {
    return (
      <>
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
        <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
          Course not found
        </h1>
        <p>
          <Link to="/">Return to course catalogue</Link>
        </p>
      </>
    );
  }

  return (
    <>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
      <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
        {data.title}
      </h1>

      <p style={{ marginBottom: '2rem' }}>
        <Link to="/">← Back to courses</Link>
      </p>

      <ol
        aria-label={`Lessons in ${data.title}`}
        style={{ paddingLeft: '1.25rem' }}
      >
        {data.lessons.map((lesson, index) => (
          <li key={lesson.id} style={{ marginBottom: '1rem' }}>
            <Link
              to={`/lesson/${lesson.id}`}
              aria-label={`Lesson ${index + 1}: ${lesson.title}${lesson.completed ? ' — completed' : ''} — ${lesson.durationMinutes} minutes`}
              style={{ fontSize: '1.1rem' }}
            >
              {lesson.title}
            </Link>
            {' '}
            <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
              (~{lesson.durationMinutes} min)
              {lesson.completed && (
                <span aria-hidden="true"> ✓</span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </>
  );
}
