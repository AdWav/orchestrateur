# UI mobile-first

Ce dossier contient le socle `web-native` du projet:

- `Vite`
- `React`
- `TypeScript`
- `Ionic React`
- `Capacitor`
- `TanStack Query`

## Demarrage local

```bash
cd ui
cp .env.example .env
npm install
npm run dev
```

Par defaut, le frontend parle a l'API locale sur `http://localhost:8000`.

## Scripts utiles

```bash
npm run dev
npm run build
npm run preview
npm run cap:sync
npm run cap:open:android
npm run cap:open:ios
```

## Workflow mobile

1. developper l'UI web avec `npm run dev`
2. construire les assets avec `npm run cap:sync`
3. ouvrir le projet natif avec `npm run cap:open:android`
4. sur macOS, ouvrir aussi `npm run cap:open:ios`

Les projets natifs ne sont pas encore generes dans ce depot. Tu pourras les creer plus tard avec:

```bash
npx cap add android
npx cap add ios
```
