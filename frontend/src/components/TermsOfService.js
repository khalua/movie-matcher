import React from 'react';
import './LegalPage.css';

function TermsOfService() {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Terms of Service</h1>
        <p className="effective-date">Effective Date: January 30, 2025</p>

        <section>
          <h2>1. Acceptance of Terms</h2>
          <p>
            By accessing or using Movie Matcher ("the Service"), you agree to be bound by these
            Terms of Service. If you do not agree to these terms, please do not use the Service.
          </p>
        </section>

        <section>
          <h2>2. Description of Service</h2>
          <p>
            Movie Matcher is a web application that helps groups of people find movies they all
            want to watch. Users can create or join "circles" (groups), swipe on movies to indicate
            preferences, and discover movies that all circle members have liked.
          </p>
        </section>

        <section>
          <h2>3. User Accounts</h2>
          <ul>
            <li>You must provide accurate information when creating an account</li>
            <li>You are responsible for maintaining the security of your account credentials</li>
            <li>You must be at least 13 years old to use the Service</li>
            <li>One person may not maintain more than one account</li>
            <li>You are responsible for all activity that occurs under your account</li>
          </ul>
        </section>

        <section>
          <h2>4. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul>
            <li>Use the Service for any unlawful purpose</li>
            <li>Harass, abuse, or harm other users</li>
            <li>Attempt to gain unauthorized access to any part of the Service</li>
            <li>Interfere with or disrupt the Service or servers</li>
            <li>Use automated means to access the Service without permission</li>
            <li>Impersonate any person or entity</li>
            <li>Upload malicious code or content</li>
          </ul>
        </section>

        <section>
          <h2>5. Circles and Social Features</h2>
          <ul>
            <li>Circle administrators can invite other users and manage circle membership</li>
            <li>Your movie preferences (likes/dislikes) are shared with other members of your circles</li>
            <li>Circle administrators may remove members at their discretion</li>
            <li>You can leave any circle at any time</li>
          </ul>
        </section>

        <section>
          <h2>6. Content and Movie Data</h2>
          <p>
            Movie information displayed in the Service is sourced from third-party databases.
            We do not guarantee the accuracy, completeness, or availability of movie data.
            Movie posters and descriptions are the property of their respective owners.
          </p>
        </section>

        <section>
          <h2>7. Intellectual Property</h2>
          <p>
            The Movie Matcher application, including its design, features, and code, is owned by us
            and protected by intellectual property laws. You may not copy, modify, or distribute
            any part of the Service without permission.
          </p>
        </section>

        <section>
          <h2>8. Privacy</h2>
          <p>
            Your use of the Service is also governed by our <a href="/privacy">Privacy Policy</a>,
            which describes how we collect, use, and protect your personal information.
          </p>
        </section>

        <section>
          <h2>9. Disclaimer of Warranties</h2>
          <p>
            THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
            EITHER EXPRESS OR IMPLIED. WE DO NOT WARRANT THAT THE SERVICE WILL BE UNINTERRUPTED,
            SECURE, OR ERROR-FREE.
          </p>
        </section>

        <section>
          <h2>10. Limitation of Liability</h2>
          <p>
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE SHALL NOT BE LIABLE FOR ANY INDIRECT,
            INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF
            THE SERVICE.
          </p>
        </section>

        <section>
          <h2>11. Account Termination</h2>
          <p>
            We reserve the right to suspend or terminate your account at any time for violations
            of these terms or for any other reason at our discretion. You may delete your account
            at any time through the application settings.
          </p>
        </section>

        <section>
          <h2>12. Changes to Terms</h2>
          <p>
            We may modify these Terms of Service at any time. We will notify users of significant
            changes by posting a notice in the application or sending an email. Continued use of
            the Service after changes constitutes acceptance of the new terms.
          </p>
        </section>

        <section>
          <h2>13. Governing Law</h2>
          <p>
            These terms shall be governed by and construed in accordance with applicable laws,
            without regard to conflict of law principles.
          </p>
        </section>

        <section>
          <h2>14. Contact</h2>
          <p>
            If you have questions about these Terms of Service, please contact us at:
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

export default TermsOfService;
