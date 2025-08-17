# M&A Newsletter - Portfolio Integration

This folder contains everything you need to add M&A newsletter signup to your portfolio website.

## What's Included

```
portfolio-transfer/
├── pages/newsletter/
│   ├── signup.js         ← Newsletter signup page
│   └── unsubscribe.js    ← Newsletter unsubscribe page
├── lib/
│   └── supabase.js       ← Supabase database client
├── .env.local.example    ← Environment variables template
├── package.json          ← Dependencies to install
└── README.md            ← This file
```

## Installation Steps

### 1. Copy Files to Your Portfolio
Copy the entire contents of this folder to your portfolio website:
- Copy `pages/newsletter/` folder to your portfolio
- Copy `lib/supabase.js` to your portfolio  
- Copy `.env.local.example` content to your `.env.local`

### 2. Install Dependencies
In your portfolio directory:
```bash
npm install @supabase/supabase-js
```

### 3. Configure Environment Variables
Rename `.env.local.example` to `.env.local` and fill in your values:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. Set Up Supabase Database
Run this SQL in your Supabase dashboard:
```sql
CREATE TABLE ma_subscribers (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified BOOLEAN DEFAULT TRUE
);

-- Enable Row Level Security
ALTER TABLE ma_subscribers ENABLE ROW LEVEL SECURITY;

-- Allow public inserts (signup) and deletes (unsubscribe)
CREATE POLICY "Anyone can signup" ON ma_subscribers
    FOR INSERT WITH CHECK (true);
    
CREATE POLICY "Anyone can unsubscribe" ON ma_subscribers
    FOR DELETE USING (true);
```

### 5. Add Navigation Link
Add a link to your newsletter signup in your portfolio navigation:
```jsx
<Link href="/newsletter/signup">
  📧 M&A Newsletter
</Link>
```

## Test the Integration

1. Start your portfolio: `npm run dev`
2. Visit: `http://localhost:3000/newsletter/signup`
3. Enter test email address
4. Check Supabase dashboard for new subscriber
5. Run your M&A pipeline to send newsletter

## Complete Flow

```
Portfolio Signup → Supabase → M&A Pipeline → Resend → Newsletter Sent
```

Your M&A pipeline automatically pulls subscribers from the same database! 🎯