# Roadmap

1. Integration with Acontext (Context Awareness)
Goal: Make Repo-Artist "learn" from user refinements.

How:

Initialize AcontextClient in the backend.

Every time a user generates an image -> Log the repo structure + Prompt used as a "Session".

Every time a user refines an image (e.g. "Make it cyberpunk") -> Log this as feedback/correction.

The Win: In future runs, query Acontext for "similar repos" (e.g., Python/FastAPI) and apply the "Cyberpunk" style automatically if that's what users prefer.​

2. Production Deployment (SaaS)
Goal: Move from Localhost to a hosted URL (repo-artist.com).

Action:

Frontend: Deploy to Vercel/Netlify.

Backend: Deploy to Railway/Render/fly.io (Dockerized).

Database: Add a PostgreSQL/SQLite volume to store the session data (unless Acontext handles it all).

