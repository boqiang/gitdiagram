[![Image](./docs/readme_img.png "GitDiagram Front Page")](https://gitdiagram.com/)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
[![Kofi](https://img.shields.io/badge/Kofi-F16061.svg?logo=ko-fi&logoColor=white)](https://ko-fi.com/ahmedkhaleel2004)

# GitDiagram

Turn any GitHub repository into an interactive diagram for visualization in seconds.

You can also replace `hub` with `diagram` in any Github URL to access its diagram.

## 🚀 Features

- 👀 **Instant Visualization**: Convert any GitHub repository structure into a system design / architecture diagram
- 🎨 **Interactivity**: Click on components to navigate directly to source files and relevant directories
- ⚡ **Fast Generation**: Choose between OpenAI o3-mini or local Ollama for diagram generation
- 🔄 **Customization**: Modify and regenerate diagrams with custom instructions
- 🌐 **API Access**: Public API available for integration (WIP)

## ⚙️ Tech Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS, ShadCN
- **Backend**: FastAPI, Python, Server Actions
- **Database**: PostgreSQL (with Drizzle ORM)
- **AI**: OpenAI o3-mini or Ollama (local LLM)
- **Deployment**: Vercel (Frontend), EC2 (Backend)
- **CI/CD**: GitHub Actions
- **Analytics**: PostHog, Api-Analytics

## 🤔 About

I created this because I wanted to contribute to open-source projects but quickly realized their codebases are too massive for me to dig through manually, so this helps me get started - but it's definitely got many more use cases!

Given any public (or private!) GitHub repository it generates diagrams in Mermaid.js with either OpenAI's o3-mini or Ollama (a local LLM)!

I extract information from the file tree and README for details and interactivity (you can click components to be taken to relevant files and directories)

Most of what you might call the "processing" of this app is done with prompt engineering - see `/backend/app/prompts.py`. This basically extracts and pipelines data and analysis for a larger action workflow, ending in the diagram code.

## 🔒 How to diagram private repositories

You can simply click on "Private Repos" in the header and follow the instructions by providing a GitHub personal access token with the `repo` scope.

You can also self-host this app locally (backend separated as well!) with the steps below.

## 🛠️ Self-hosting / Local Development

1. Clone the repository

```bash
git clone https://github.com/ahmedkhaleel2004/gitdiagram.git
cd gitdiagram
```

2. Install dependencies

```bash
pnpm i
```

3. Set up environment variables (create .env)

```bash
cp .env.example .env
```

Then edit the `.env` file with your configuration:
- For OpenAI: Add your OpenAI API key
- For Ollama: Install Ollama locally and set `DEFAULT_LLM_PROVIDER=ollama`
- Optional: Add GitHub personal access token for increased rate limits

4. If using Ollama, install and start it:

```bash
# On macOS
brew install ollama
ollama serve

# In another terminal
ollama pull mistral
```

5. Run backend

```bash
docker-compose up --build -d
```

Logs available at `docker-compose logs -f`
The FastAPI server will be available at `localhost:8000`

6. Start local database

```bash
chmod +x start-database.sh
./start-database.sh
```

When prompted to generate a random password, input yes.
The Postgres database will start in a container at `localhost:5432`

7. Initialize the database schema

```bash
pnpm db:push
```

You can view and interact with the database using `pnpm db:studio`

8. Run Frontend

```bash
pnpm dev
```

You can now access the website at `localhost:3000` and edit the rate limits defined in `backend/app/routers/generate.py` in the generate function decorator.

## 🔄 Switching LLM Providers

GitDiagram supports two LLM providers:

1. **OpenAI o3-mini** (Default)
   - Requires an OpenAI API key
   - Hosted solution, pay-per-use
   - Best for production use

2. **Ollama** (Local)
   - Free to use
   - Runs locally on your machine
   - Great for development and testing
   - No API key needed
   - Currently uses the Mistral model

To switch providers:
1. Set `DEFAULT_LLM_PROVIDER` in your `.env` file to either `openai` or `ollama`
2. If using Ollama, make sure it's installed and running locally
3. Restart the backend service

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

Shoutout to [Romain Courtois](https://github.com/cyclotruc)'s [Gitingest](https://gitingest.com/) for inspiration and styling

## 📈 Rate Limits

I am currently hosting it for free with no rate limits though this is somewhat likely to change in the future.

## 🤔 Future Steps

- Implement font-awesome icons in diagram
- Implement an embedded feature like star-history.com but for diagrams. The diagram could also be updated progressively as commits are made.
- Add support for more Ollama models
- Add configuration UI for switching LLM providers
