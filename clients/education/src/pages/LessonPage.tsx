/**
 * Lesson player page — audio-primary learning experience.
 *
 * Accessibility:
 * - Audio transcript is shown by default (never hidden-only).
 * - Navigation to previous/next lesson is keyboard accessible.
 * - Lesson title is the <h1>; focus moves here on mount.
 * - "Mark as complete" button uses aria-pressed for toggle state.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AudioPlayer from '../components/AudioPlayer';

interface LessonData {
  id: string;
  title: string;
  courseId: string;
  courseTitle: string;
  audioSrc: string;
  transcript: string;
  prevLesson?: string;
  nextLesson?: string;
}

// Placeholder lessons — replaced by API fetch in production.
const LESSON_DATA: Record<string, LessonData> = {
  'gs-1': {
    id: 'gs-1',
    title: 'Welcome and overview',
    courseId: 'getting-started',
    courseTitle: 'Getting Started with Blind Assistant',
    audioSrc: '/audio/gs-1-welcome.mp3',
    transcript:
      'Welcome to Blind Assistant. In this course you will learn how to set up the app, ' +
      'configure your voice preferences, and complete real-world tasks entirely by speaking. ' +
      'You never need to touch a mouse or read a screen. Everything works by voice.',
    nextLesson: 'gs-2',
  },
  'gs-2': {
    id: 'gs-2',
    title: 'Installing the app',
    courseId: 'getting-started',
    courseTitle: 'Getting Started with Blind Assistant',
    audioSrc: '/audio/gs-2-install.mp3',
    transcript:
      'This lesson walks you through installing Blind Assistant on your phone or computer. ' +
      'The installer speaks every step aloud. You only need to follow what you hear.',
    prevLesson: 'gs-1',
    nextLesson: 'gs-3',
  },
};

export default function LessonPage(): React.ReactElement {
  const { lessonId } = useParams<{ lessonId: string }>();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    headingRef.current?.focus();
    setCompleted(false);
  }, [lessonId]);

  const lesson = lessonId ? LESSON_DATA[lessonId] : null;

  if (!lesson) {
    return (
      <>
        {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
        <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
          Lesson not found
        </h1>
        <p>
          <Link to="/">Return to courses</Link>
        </p>
      </>
    );
  }

  return (
    <>
      {/* Breadcrumb navigation */}
      <nav aria-label="Breadcrumb" style={{ marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', gap: '0.5rem' }}>
          <li>
            <Link to="/">Courses</Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link to={`/course/${lesson.courseId}`}>{lesson.courseTitle}</Link>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page">{lesson.title}</li>
        </ol>
      </nav>

      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
      <h1 ref={headingRef} tabIndex={-1} style={{ outline: 'none' }}>
        {lesson.title}
      </h1>

      {/* Audio player with transcript */}
      <AudioPlayer
        src={lesson.audioSrc}
        title={lesson.title}
        transcript={lesson.transcript}
      />

      {/* Lesson completion */}
      <div style={{ marginTop: '2rem' }}>
        <button
          className="btn"
          aria-pressed={completed}
          onClick={() => setCompleted((v) => !v)}
          style={{ marginBottom: '1rem' }}
        >
          {completed ? 'Marked as complete ✓' : 'Mark as complete'}
        </button>

        {/* Previous / Next lesson navigation */}
        <nav
          aria-label="Lesson navigation"
          style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '1rem' }}
        >
          {lesson.prevLesson && (
            <Link
              to={`/lesson/${lesson.prevLesson}`}
              className="btn btn--secondary"
              aria-label="Previous lesson"
            >
              ← Previous
            </Link>
          )}
          {lesson.nextLesson && (
            <Link
              to={`/lesson/${lesson.nextLesson}`}
              className="btn"
              aria-label="Next lesson"
            >
              Next →
            </Link>
          )}
          {!lesson.nextLesson && (
            <Link
              to={`/course/${lesson.courseId}`}
              className="btn"
              aria-label="Back to course"
            >
              Back to course
            </Link>
          )}
        </nav>
      </div>
    </>
  );
}
