# SZU Sports Suite

This repository is being structured as an engineering-grade workspace for the SZU sports reservation product.

It currently combines:

- `apps/web` for the React control surface
- `gym_bot/` for the Python automation core and Electron shell
- `packages/` for future shared contracts, config, and UI layers
- `specs/` and `harness/` for AI-native and harness-first development
- `docs/szu-booking/` for static product prototype and reference material
- `references/` for imported design and liquid-glass references

## Repository Shape

```text
.
├── apps/
│   └── web/                    # Vite + React frontend
├── gym_bot/                    # Python booking core + Electron shell
├── packages/                   # Shared workspace packages
├── specs/                      # Feature specs
├── harness/                    # Contracts, scenarios, fixtures
├── runtime/                    # Mutable runtime state
├── docs/szu-booking/           # Product prototype and docs
├── references/                 # External design/code references
├── AI_NATIVE_HARNESS.md        # Repository engineering contract
├── DESIGN.md                   # Apple reference from getdesign
├── 风格.md                      # Project-specific frontend style rules
└── TODO.md                     # Execution backlog
```

## Run

### Web

```bash
npm install
npm run dev
```

Default URL: `http://127.0.0.1:5174`

### Python Core

```bash
cd gym_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python main.py --now
```

### Electron Shell

```bash
cd gym_bot/app
npm install
npm start
```

## Engineering Rules

Read these before substantial work:

- [AI_NATIVE_HARNESS.md](/Users/bytedance/Desktop/szu-auth-react/AI_NATIVE_HARNESS.md)
- [CLAUDE.md](/Users/bytedance/Desktop/szu-auth-react/CLAUDE.md)
- [.agent/README.md](/Users/bytedance/Desktop/szu-auth-react/.agent/README.md)
- [DESIGN.md](/Users/bytedance/Desktop/szu-auth-react/DESIGN.md)
- [风格.md](/Users/bytedance/Desktop/szu-auth-react/%E9%A3%8E%E6%A0%BC.md)

## Current Notes

- `apps/web` is now the main frontend home instead of the repository root.
- `gym_bot` is still the current source of truth for booking, auth, cookie, and agent behavior.
- `packages/` is scaffolded so shared layers can be extracted deliberately instead of staying scattered.
- `references/` keeps imported third-party design/code material out of the root.

## License

MIT
