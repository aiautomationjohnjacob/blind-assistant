/**
 * CourseCard — displays a single course in the catalogue.
 *
 * Accessibility:
 * - The card is an <article> with a heading so screen readers can enumerate
 *   all courses via the heading navigation shortcut (H key in NVDA/JAWS).
 * - The "Start course" link text includes the course title so it is
 *   unambiguous when read in isolation (link list mode in screen readers).
 * - Completion percentage is shown as text AND a progress bar (never colour alone).
 * - Card is NOT a single interactive element — the heading and link are
 *   separate focusable items so keyboard users can read before activating.
 */

import React from 'react';
import { Link } from 'react-router-dom';

export interface Course {
  id: string;
  title: string;
  description: string;
  lessonCount: number;
  completedLessons: number;
  durationMinutes: number;
}

interface CourseCardProps {
  course: Course;
}

export default function CourseCard({ course }: CourseCardProps): React.ReactElement {
  const completionPct =
    course.lessonCount > 0
      ? Math.round((course.completedLessons / course.lessonCount) * 100)
      : 0;

  const isStarted = course.completedLessons > 0;
  const isComplete = course.completedLessons >= course.lessonCount;

  return (
    <article
      aria-label={course.title}
      style={{
        border: '1px solid #334155',
        borderRadius: '8px',
        padding: '1.5rem',
        background: '#16213e',
        marginBottom: '1.5rem',
      }}
    >
      <h2 style={{ fontSize: '1.25rem', marginTop: 0 }}>{course.title}</h2>
      <p style={{ color: '#94a3b8' }}>{course.description}</p>

      <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
        {course.lessonCount} lessons &bull; ~{course.durationMinutes} minutes total
      </p>

      {/* Progress — text + bar so colour is never the only indicator */}
      {isStarted && (
        <div style={{ marginBottom: '1rem' }}>
          <p style={{ fontSize: '0.9rem', marginBottom: '0.25rem' }}>
            {isComplete
              ? 'Complete!'
              : `${course.completedLessons} of ${course.lessonCount} lessons done (${completionPct}%)`}
          </p>
          <div
            className="progress-bar"
            role="progressbar"
            aria-valuenow={completionPct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`${completionPct}% of ${course.title} complete`}
          >
            <div className="progress-bar__fill" style={{ width: `${completionPct}%` }} />
          </div>
        </div>
      )}

      <Link
        to={`/course/${course.id}`}
        className="btn"
        aria-label={
          isComplete
            ? `Review ${course.title}`
            : isStarted
            ? `Continue ${course.title}`
            : `Start course: ${course.title}`
        }
      >
        {isComplete ? 'Review' : isStarted ? 'Continue' : 'Start course'}
      </Link>
    </article>
  );
}
