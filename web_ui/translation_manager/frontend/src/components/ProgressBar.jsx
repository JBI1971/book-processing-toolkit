import React from 'react';

/**
 * Progress Bar Component with Color Coding
 *
 * Color coding:
 * - 0-33%: Red/warning
 * - 34-66%: Yellow/in-progress
 * - 67-99%: Blue/almost-done
 * - 100%: Green/complete
 */
function ProgressBar({
  current,
  total,
  label,
  showPercentage = true,
  showFraction = true,
  height = '24px',
  animated = false
}) {
  const percentage = total > 0 ? (current / total) * 100 : 0;
  const displayPercentage = Math.min(100, percentage).toFixed(1);

  // Determine color based on percentage
  const getColor = () => {
    if (percentage === 100) return '#27ae60'; // Green - complete
    if (percentage >= 67) return '#3498db'; // Blue - almost done
    if (percentage >= 34) return '#f39c12'; // Yellow/orange - in progress
    return '#e74c3c'; // Red - just started/warning
  };

  const color = getColor();

  return (
    <div style={{ width: '100%' }}>
      {label && (
        <div style={{
          fontSize: '12px',
          marginBottom: '4px',
          color: '#555',
          fontWeight: '500'
        }}>
          {label}
        </div>
      )}
      <div style={{
        width: '100%',
        height,
        backgroundColor: '#ecf0f1',
        borderRadius: '4px',
        overflow: 'hidden',
        position: 'relative',
        border: '1px solid #ddd'
      }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          backgroundColor: color,
          transition: 'width 0.3s ease, background-color 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          ...(animated && {
            backgroundImage: 'linear-gradient(45deg, rgba(255,255,255,.15) 25%, transparent 25%, transparent 50%, rgba(255,255,255,.15) 50%, rgba(255,255,255,.15) 75%, transparent 75%, transparent)',
            backgroundSize: '1rem 1rem',
            animation: 'progress-bar-stripes 1s linear infinite'
          })
        }}>
          {percentage > 15 && (
            <span style={{
              color: 'white',
              fontSize: '12px',
              fontWeight: '600',
              textShadow: '0 1px 2px rgba(0,0,0,0.3)',
              position: 'absolute',
              whiteSpace: 'nowrap'
            }}>
              {showPercentage && `${displayPercentage}%`}
              {showPercentage && showFraction && ' '}
              {showFraction && `(${current}/${total})`}
            </span>
          )}
        </div>
        {percentage <= 15 && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '12px',
            fontWeight: '600',
            color: '#555',
            whiteSpace: 'nowrap'
          }}>
            {showPercentage && `${displayPercentage}%`}
            {showPercentage && showFraction && ' '}
            {showFraction && `(${current}/${total})`}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Multi-level Progress Display
 * Shows work, chapter, and block progress in a hierarchical view
 */
function MultiLevelProgress({ detailedProgress, workProgress = 0 }) {
  if (!detailedProgress) {
    return (
      <ProgressBar
        current={workProgress}
        total={100}
        label="Work Progress"
        showFraction={false}
        animated={workProgress > 0 && workProgress < 100}
      />
    );
  }

  const {
    total_chapters = 0,
    completed_chapters = 0,
    total_blocks = 0,
    completed_blocks = 0,
    current_chapter_blocks = 0,
    current_chapter_completed = 0,
    current_chapter = null
  } = detailedProgress;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Overall Work Progress */}
      <ProgressBar
        current={workProgress}
        total={100}
        label="Work Progress"
        showFraction={false}
        animated={workProgress > 0 && workProgress < 100}
      />

      {/* Chapter Progress */}
      {total_chapters > 0 && (
        <ProgressBar
          current={completed_chapters}
          total={total_chapters}
          label="Chapter Progress"
          animated={completed_chapters < total_chapters}
        />
      )}

      {/* Current Chapter Progress */}
      {current_chapter && current_chapter_blocks > 0 && (
        <ProgressBar
          current={current_chapter_completed}
          total={current_chapter_blocks}
          label={`Current Chapter: ${current_chapter}`}
          height="20px"
          animated={current_chapter_completed < current_chapter_blocks}
        />
      )}

      {/* Block Progress */}
      {total_blocks > 0 && (
        <ProgressBar
          current={completed_blocks}
          total={total_blocks}
          label="Total Block Progress"
          height="20px"
        />
      )}
    </div>
  );
}

/**
 * Compact Progress Badge
 * Shows just the percentage with color coding
 */
function ProgressBadge({ percentage }) {
  const getColor = () => {
    if (percentage === 100) return '#27ae60';
    if (percentage >= 67) return '#3498db';
    if (percentage >= 34) return '#f39c12';
    return '#e74c3c';
  };

  return (
    <span style={{
      display: 'inline-block',
      padding: '4px 8px',
      borderRadius: '12px',
      backgroundColor: getColor(),
      color: 'white',
      fontSize: '12px',
      fontWeight: '600',
      minWidth: '50px',
      textAlign: 'center'
    }}>
      {percentage.toFixed(0)}%
    </span>
  );
}

export { ProgressBar, MultiLevelProgress, ProgressBadge };
export default ProgressBar;
