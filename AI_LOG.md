# AI Development Log

## AI Tools Used

1. **Cascade (Claude-powered AI assistant)** - Primary coding assistant for building the entire application
   - Used for: Architecture decisions, code implementation, debugging, UI design
   - Platform: IDE integration

## Key AI Conversations

### Conversation 1: OAuth PKCE Fix
**Context**: The Gmail OAuth integration was failing with "Missing code verifier" error.

**Problem**: The Flow object couldn't be pickled to preserve the PKCE code verifier between authorization and callback routes.

**AI's initial approach**: Try to pickle the Flow object and store it in the session.
**Result**: Failed with `AttributeError: Can't pickle local object 'OAuth2Session.__init__.<locals>.<lambda>'`

**AI's second approach**: Disable PKCE by setting `code_verifier=None`.
**Result**: Still failed with the same error.

**Final solution (provided by user)**: Store the Flow object in server memory (`oauth_flows = {}` dictionary) using the state as key, and retrieve it in the callback. This avoids session cookie issues and pickling problems.

**Key prompt from user**:
```
Let's fix this more reliably for your local testing.
Step 1. Add this near the top of app.py
oauth_flows = {}

Step 2. Replace your /authorize function
...

Step 3. Replace your /oauth2callback function
...
```

### Conversation 2: Building the Full Application
**Context**: Transitioning from a simple Gmail test to the full Shop Credit Tracker application.

**Key prompt from user**:
```
do this one
here for alerts i have kept gmail make sure those endpoints are correct otherwise i will get error
and make sure the ui is dynamic and easy to use and navigate
and keep a loading page also
and make sure write clean code
dont make it too complex write simple code with less number of lines and good approach
```

**AI's approach**:
- Built a complete Flask app with SQLite database
- Created mobile-friendly UI using Tailwind CSS
- Integrated the existing Gmail OAuth endpoints
- Added login system with session management
- Implemented customer and transaction management
- Added loading page with spinner animation

## Times AI Was Wrong or Gave Poor Results

### 1. OAuth Session Storage Approach
**What happened**: AI tried to use Flask session to store OAuth state and code verifier.

**How I noticed**: The application kept failing with `KeyError: 'state'` when the callback was called, because the browser wasn't preserving session cookies between localhost and 127.0.0.1.

**How I fixed it**: User provided the solution to use server-side dictionary storage instead of session cookies. This was more reliable for local development.

### 2. Pickling the Flow Object
**What happened**: AI attempted to pickle the Flow object to preserve PKCE verifier.

**How I noticed**: Got error `AttributeError: Can't pickle local object 'OAuth2Session.__init__.<locals>.<lambda>'` when trying to run the app.

**How I fixed it**: Abandoned the pickling approach and used the in-memory dictionary solution provided by the user.

## Decision Where I Disagreed with AI

### UI Framework Choice
**AI's suggestion**: Could have used a more complex frontend framework like React or Vue.js with a separate build process.

**My decision**: Chose to use Tailwind CSS via CDN with simple Jinja2 templates in Flask.

**Why I disagreed**:
- The requirement was for a simple, easy-to-use app that Ravi can run locally
- React/Vue would add complexity with build tools, npm, and deployment
- Tailwind via CDN gives a modern UI without the overhead
- Single-file Python app is easier for Ravi to understand and modify if needed
- Faster development time, which aligns with the "keep it simple" requirement

## Summary

The AI was very helpful for:
- Rapid prototyping of the application structure
- Writing clean, readable code
- Implementing the database schema and queries
- Creating a mobile-responsive UI with Tailwind CSS

The main challenges were around OAuth integration, which required user guidance to solve correctly. The AI's initial approaches were reasonable but didn't account for the specific constraints of local development with OAuth.
