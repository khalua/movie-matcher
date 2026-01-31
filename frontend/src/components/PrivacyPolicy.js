import React from 'react';
import './LegalPage.css';

function PrivacyPolicy() {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Privacy Policy</h1>
        <p className="effective-date">Effective Date: January 30, 2025</p>

        <section>
          <h2>Introduction</h2>
          <p>
            Movie Matcher ("we," "our," or "us") respects your privacy and is committed to protecting
            your personal data. This privacy policy explains how we collect, use, and safeguard your
            information when you use our movie matching application.
          </p>
        </section>

        <section>
          <h2>Information We Collect</h2>
          <h3>Information you provide:</h3>
          <ul>
            <li><strong>Account Information:</strong> Email address, display name, and password when you create an account</li>
            <li><strong>Google Account Data:</strong> If you sign in with Google, we receive your email address and name from your Google profile</li>
            <li><strong>Movie Preferences:</strong> Your likes and dislikes of movies within the application</li>
            <li><strong>Circle Memberships:</strong> Information about the groups you create or join</li>
          </ul>

          <h3>Information collected automatically:</h3>
          <ul>
            <li><strong>Usage Data:</strong> Pages viewed, features used, and interactions within the app</li>
            <li><strong>Device Information:</strong> Browser type, device type, and general location (country/region)</li>
          </ul>
        </section>

        <section>
          <h2>How We Use Your Information</h2>
          <p>We use your information to:</p>
          <ul>
            <li>Provide and maintain the Movie Matcher service</li>
            <li>Match your movie preferences with other users in your circles</li>
            <li>Send you notifications about matches and circle activity</li>
            <li>Improve and optimize our application</li>
            <li>Communicate with you about your account or service updates</li>
          </ul>
        </section>

        <section>
          <h2>Information Sharing</h2>
          <p>We do not sell your personal information. We may share your information in these limited circumstances:</p>
          <ul>
            <li><strong>With Circle Members:</strong> Your movie preferences and display name are visible to other members of circles you join</li>
            <li><strong>Service Providers:</strong> We may use third-party services for hosting, analytics, and email delivery</li>
            <li><strong>Legal Requirements:</strong> We may disclose information if required by law or to protect our rights</li>
          </ul>
        </section>

        <section>
          <h2>Data Security</h2>
          <p>
            We implement appropriate security measures to protect your personal information.
            However, no method of transmission over the internet is 100% secure, and we cannot
            guarantee absolute security.
          </p>
        </section>

        <section>
          <h2>Your Rights</h2>
          <p>You have the right to:</p>
          <ul>
            <li>Access the personal data we hold about you</li>
            <li>Request correction of inaccurate data</li>
            <li>Request deletion of your account and associated data</li>
            <li>Withdraw consent for data processing</li>
          </ul>
          <p>To exercise these rights, please contact us using the information below.</p>
        </section>

        <section>
          <h2>Cookies and Tracking</h2>
          <p>
            We use cookies and similar technologies to maintain your session and remember your
            preferences. We may also use analytics services to understand how users interact
            with our application.
          </p>
        </section>

        <section>
          <h2>Third-Party Services</h2>
          <p>Our application integrates with:</p>
          <ul>
            <li><strong>Google Sign-In:</strong> For authentication. Google's privacy policy applies to data collected by Google.</li>
            <li><strong>OMDB API:</strong> For movie information. We send search queries but no personal data.</li>
          </ul>
        </section>

        <section>
          <h2>Children's Privacy</h2>
          <p>
            Movie Matcher is not intended for children under 13 years of age. We do not knowingly
            collect personal information from children under 13.
          </p>
        </section>

        <section>
          <h2>Changes to This Policy</h2>
          <p>
            We may update this privacy policy from time to time. We will notify you of any changes
            by posting the new policy on this page and updating the effective date.
          </p>
        </section>

        <section>
          <h2>Contact Us</h2>
          <p>
            If you have questions about this privacy policy or our data practices, please contact us at:
          </p>
          <p className="contact-info">
            Email: mm-admin@yerko.com
          </p>
        </section>

        <div className="back-link">
          <a href="/">← Back to Movie Matcher</a>
        </div>
      </div>
    </div>
  );
}

export default PrivacyPolicy;
