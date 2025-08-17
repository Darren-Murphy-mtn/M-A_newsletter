// Newsletter Signup Component for Your Portfolio
// Add this to your portfolio: pages/newsletter/signup.js

import { useState } from 'react';
import Head from 'next/head';
import { supabase } from '../../lib/supabase';

export default function NewsletterSignup() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus('');

    try {
      const { error } = await supabase
        .from('ma_subscribers')
        .insert([
          { 
            email: email.toLowerCase().trim(),
            verified: true
          }
        ]);

      if (error) {
        if (error.code === '23505') {
          setStatus('Email already subscribed!');
        } else {
          throw error;
        }
      } else {
        setStatus('success');
        setEmail('');
      }
    } catch (error) {
      console.error('Subscription error:', error);
      setStatus('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>M&A Newsletter Signup</title>
        <meta name="description" content="Subscribe to weekly M&A deals and insights" />
      </Head>
      
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white rounded-lg shadow-xl p-8">
          
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">M&A Newsletter</h1>
            <p className="text-gray-600 text-lg">
              Weekly insights on mergers, acquisitions & finance deals
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                placeholder="your@email.com"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-3 px-6 rounded-lg transition duration-200"
            >
              {loading ? 'Subscribing...' : 'Subscribe to Newsletter'}
            </button>
          </form>

          {/* Success Message */}
          {status === 'success' && (
            <div className="mt-6 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
              <div className="flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                🎉 Successfully subscribed! You'll receive weekly M&A insights.
              </div>
            </div>
          )}

          {/* Error Message */}
          {status && status !== 'success' && (
            <div className="mt-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
              {status}
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 text-center text-sm text-gray-500">
            <p>• No spam, unsubscribe anytime</p>
            <p>• Weekly delivery every Monday</p>
            <div className="mt-4">
              <a 
                href="/newsletter/unsubscribe" 
                className="text-blue-600 hover:text-blue-700 underline"
              >
                Unsubscribe
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}