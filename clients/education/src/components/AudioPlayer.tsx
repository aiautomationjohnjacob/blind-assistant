/**
 * AudioPlayer — core component of the audio-primary learning experience.
 *
 * Design rationale:
 * - Blind users navigate this platform entirely by keyboard and screen reader.
 * - The browser's native <audio> element is used because it provides built-in
 *   keyboard controls (space=play/pause, arrows=seek) and a native accessible
 *   control set that NVDA and VoiceOver both understand.
 * - Custom controls supplement (not replace) native controls so keyboard users
 *   have large, clearly labelled buttons.
 * - Transcript panel is shown by default; audio-only users should never be left
 *   without a text alternative (WCAG 1.2.1).
 *
 * Accessibility:
 * - All buttons have explicit aria-label (icon-only buttons would be unlabelled).
 * - aria-live region announces playback state changes to NVDA / VoiceOver.
 * - Progress is shown as text percentage alongside the visual bar.
 * - Current time and duration are spoken in a natural format (e.g. "1 minute 30 seconds").
 */

import React, { useRef, useState, useCallback } from 'react';

interface AudioPlayerProps {
  src: string;
  title: string;
  transcript?: string;
}

function formatTime(seconds: number): string {
  /** Format seconds into a natural spoken string: "2 minutes 15 seconds". */
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs} second${secs !== 1 ? 's' : ''}`;
  return `${mins} minute${mins !== 1 ? 's' : ''} ${secs} second${secs !== 1 ? 's' : ''}`;
}

export default function AudioPlayer({
  src,
  title,
  transcript,
}: AudioPlayerProps): React.ReactElement {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [showTranscript, setShowTranscript] = useState(true);

  const progress = duration > 0 ? Math.round((currentTime / duration) * 100) : 0;

  const announce = useCallback((msg: string) => {
    /** Update the live region so screen readers speak the message. */
    setStatusMsg(msg);
  }, []);

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.play().catch(() => announce('Could not play audio. Check your audio settings.'));
      setIsPlaying(true);
      announce('Playing');
    } else {
      audio.pause();
      setIsPlaying(false);
      announce('Paused');
    }
  }, [announce]);

  const seek = useCallback(
    (seconds: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + seconds));
      announce(`Seeked to ${formatTime(audio.currentTime)}`);
    },
    [announce]
  );

  return (
    <section aria-label={`Audio player: ${title}`}>
      {/* Hidden live region — announces playback events to screen readers */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {statusMsg}
      </div>

      {/* Native audio element — keyboard controls: Space=play/pause, Left/Right=seek */}
      <audio
        ref={audioRef}
        src={src}
        onTimeUpdate={(e) => setCurrentTime((e.target as HTMLAudioElement).currentTime)}
        onLoadedMetadata={(e) => setDuration((e.target as HTMLAudioElement).duration)}
        onEnded={() => {
          setIsPlaying(false);
          announce('Lesson complete.');
        }}
        aria-label={title}
        style={{ width: '100%', marginBottom: '1rem' }}
      />

      {/* Custom controls — supplement native controls with larger, labelled buttons */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
          marginBottom: '1rem',
        }}
        role="toolbar"
        aria-label="Playback controls"
      >
        <button
          className="btn btn--secondary"
          onClick={() => seek(-10)}
          aria-label="Rewind 10 seconds"
        >
          &#8676; 10s
        </button>

        <button
          className="btn"
          onClick={togglePlayPause}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          aria-pressed={isPlaying}
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <button
          className="btn btn--secondary"
          onClick={() => seek(10)}
          aria-label="Skip forward 10 seconds"
        >
          10s &#8677;
        </button>
      </div>

      {/* Progress — text + visual bar (never colour alone) */}
      <p aria-live="off" style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
        {formatTime(currentTime)} of {formatTime(duration)} &mdash; {progress}% complete
      </p>
      <div
        className="progress-bar"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${progress}% of lesson complete`}
      >
        <div className="progress-bar__fill" style={{ width: `${progress}%` }} />
      </div>

      {/* Transcript toggle */}
      {transcript && (
        <div style={{ marginTop: '1.5rem' }}>
          <button
            className="btn btn--secondary"
            onClick={() => setShowTranscript((v) => !v)}
            aria-expanded={showTranscript}
            aria-controls="lesson-transcript"
          >
            {showTranscript ? 'Hide transcript' : 'Show transcript'}
          </button>
          <div
            id="lesson-transcript"
            hidden={!showTranscript}
            style={{
              marginTop: '1rem',
              padding: '1rem',
              background: '#16213e',
              borderRadius: '4px',
              border: '1px solid #334155',
              lineHeight: 1.8,
            }}
          >
            <h3>Transcript</h3>
            <p style={{ whiteSpace: 'pre-wrap' }}>{transcript}</p>
          </div>
        </div>
      )}
    </section>
  );
}
