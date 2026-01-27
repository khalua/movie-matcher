import React from 'react';
import { useCircle } from '../contexts/CircleContext';
import './CircleSelector.css';

const CircleSelector = () => {
  const { currentCircle, circles, switchCircle } = useCircle();

  if (!currentCircle || circles.length === 0) return null;

  return (
    <div className="circle-selector">
      <select
        value={currentCircle.id}
        onChange={(e) => switchCircle(parseInt(e.target.value))}
        className="circle-dropdown"
      >
        {circles.map(circle => (
          <option key={circle.id} value={circle.id}>
            {circle.name}{circle.is_member === false ? ' (viewing)' : ''}
          </option>
        ))}
      </select>
    </div>
  );
};

export default CircleSelector;
