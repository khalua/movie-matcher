import React, { useState } from 'react';
import './Welcome.css';

const Welcome = ({ onComplete, circle }) => {
  const [currentStep, setCurrentStep] = useState(0);

  // Build dynamic content based on circle info
  const adminName = circle?.admin_name;
  const moviesReadyStep = adminName
    ? {
        icon: '🎯',
        title: 'Movies Ready to Swipe',
        description: `${adminName} has already added great movies to this circle. Start swiping right away!`,
        highlight: 'Jump right in'
      }
    : {
        icon: '🎯',
        title: 'Movies Ready to Swipe',
        description: 'Your circle admin has already added great movies to watch. Start swiping right away!',
        highlight: 'Jump right in'
      };

  const steps = [
    {
      icon: '🎬',
      title: 'Welcome to Movie Matcher!',
      description: 'Find movies everyone in your group will love. No more endless debates about what to watch!',
      highlight: null
    },
    moviesReadyStep,
    {
      icon: '🤔',
      title: 'Swipe to Vote',
      description: 'Swipe right or tap the green button if you\'d watch it. Swipe left or tap red if it\'s not for you.',
      highlight: 'Your votes are private until everyone matches'
    },
    {
      icon: '✨',
      title: 'Discover Matches',
      description: 'When everyone in your circle likes the same movie, it becomes a match! Check the Matches screen to see what to watch.',
      highlight: 'Perfect for movie nights'
    },
    {
      icon: '🍿',
      title: 'Watch a Damn Movie!',
      description: 'Talk to your circle, and agree to watch something. Mark it as watched and repeat.',
      highlight: 'Maybe you can discuss the movie?'
    },
    {
      icon: '⭕️',
      title: 'Invite or Create a Cew Circle',
      description: 'You can add new members to your Circle, or create a new Circle to watch movies with.',
      highlight: 'The more the merrier'
    }


  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      localStorage.setItem('hasSeenWelcome', 'true');
      onComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    localStorage.setItem('hasSeenWelcome', 'true');
    onComplete();
  };

  const step = steps[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="welcome-overlay">
      <div className="welcome-container">
        <div className="welcome-progress">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`progress-dot ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
            />
          ))}
        </div>

        <div className="welcome-content">
          <div className="welcome-icon">{step.icon}</div>
          <h1 className="welcome-title">{step.title}</h1>
          <p className="welcome-description">{step.description}</p>
          {step.highlight && (
            <div className="welcome-highlight">
              <span>{step.highlight}</span>
            </div>
          )}
        </div>

        {currentStep === 2 && (
          <div className="swipe-demo">
            <div className="demo-card">
              <div className="demo-arrows">
                <div className="demo-arrow left">
                  <span className="arrow-icon">👈</span>
                  <span className="arrow-label">Nope</span>
                </div>
                <div className="demo-movie">🎥</div>
                <div className="demo-arrow right">
                  <span className="arrow-icon">👉</span>
                  <span className="arrow-label">Like!</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="welcome-actions">
          {!isFirstStep && (
            <button className="welcome-back-link" onClick={handlePrevious}>
              Back
            </button>
          )}
          <button className="welcome-btn primary" onClick={handleNext}>
            {isLastStep ? "Let's Go!" : 'Next'}
          </button>
          <button
            className="welcome-skip-link"
            onClick={handleSkip}
            style={{ visibility: isLastStep ? 'hidden' : 'visible' }}
          >
            Skip intro
          </button>
        </div>
      </div>
    </div>
  );
};

export default Welcome;
