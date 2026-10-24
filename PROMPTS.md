# Prompts

These are the prompts I would give an AI assistant to build this app from scratch, in order. I kept them simple and one step at a time.

## 1. Start
I want to build a small web app to keep a watchlist of IOCs (indicators of compromise). An IOC can be an IPv4 address, a domain, a URL or a file hash (md5, sha1, sha256). I will use Python with FastAPI for the backend, SQLite for the database, and React with TypeScript for the frontend. First make the folders and the basic setup, nothing else yet.

## 2. Detect the type
Write a function that takes a text value and tells me what type it is: ipv4, domain, url, md5, sha1 or sha256. If it is not any of these, reject it with a clear message. Also write tests for it.

## 3. Clean up the value
People paste values in different ways, like `hxxps://evil[.]com/` or ` EVIL.com `. Make the function clean the value first: remove spaces, fix the defanged parts, lowercase the domain, remove the trailing slash and the `#fragment`. The same IOC written in different ways should come out as the exact same value. Add tests for these cases.

## 4. Database
Make the database tables. An IOC has a type, the cleaned value (must be unique), the original value, an optional note and a created time. An IOC can have many tags and a tag can be on many IOCs.

## 5. API
Make these endpoints: add an IOC, list IOCs (filter by tag and by type) and delete an IOC. If the IOC already exists, return a 409 error and show the existing one. Bad values should return a 422 with a clear message. Add tests for all of this.

## 6. Tags
Tags should be lowercase and have no duplicates. When I delete the last IOC that uses a tag, delete the tag too. Add one endpoint to list all tags.

## 7. Frontend
Make the React page. It should have a form to add an IOC (value, note, tags), a list of IOCs, filters for tag and type, and a delete button on each row. Show the error message if the add fails, and show a clear message if it is a duplicate. Never make the IOC value a clickable link, because it can be dangerous.

## 8. Run it as one app
After `npm run build`, let FastAPI serve the built frontend, so the whole app runs on one port. During development, use the Vite proxy for the `/api` calls.

## 9. Check everything
Run all the tests and the frontend build. Fix whatever fails. Then check that adding the same IOC in 3 different ways only saves it once.

## 10. README
Write a simple README. It should say how to run the app, how to run the tests, how to deploy it, what the api looks like, what assumptions I made and what is missing. Keep the language simple.

## 11. Git
Make a `.gitignore` so that venv, node_modules, `.vite` and the `.db` file never go to git. Then push the code to GitHub in small commits on a feature branch, merge it to main, and push.

## Where the AI got something wrong

- It started building the frontend in plain HTML and JavaScript. I wanted React and TypeScript, so I stopped it and it rebuilt the frontend that way.
- It added Docker files on its own, which I did not ask for. I had them removed and the README changed to run it without Docker.
- When I asked if it could run the app, it ran it in its own environment, not on my laptop. The page did not open for me until I started the backend and the frontend myself.
