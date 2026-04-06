# D•CORE Party Designer

A React Native (Expo) mobile app for event decorators to design and present party mockups to clients.

## Core Features

| Feature | Description |
|---|---|
| Drag & Drop Builder | Place balloon arches, tables, backdrops, thrones, and marquees onto a canvas |
| Color Customization | Tap any item → change its color with 40+ presets or a custom hex code |
| Venue Photo Upload | Upload a real venue photo as the canvas background for true-to-life mockups |
| Layering System | Bring items forward / send backward to stack decorations correctly |
| Save & Share | Export designs to the camera roll or share directly with clients |

## Tech Stack

- **Expo SDK 52** (managed workflow)
- **React Native 0.76**
- **react-native-svg** — vector decoration shapes
- **react-native-view-shot** — canvas capture for save/share
- **expo-image-picker** — venue photo upload
- **expo-media-library** — save to camera roll
- **expo-sharing** — share mockups with clients

## Getting Started

```bash
cd party-decorator
npm install
npx expo start
```

Then scan the QR code with **Expo Go** on your iOS or Android device.

### Building for production

```bash
npx eas build --platform ios
npx eas build --platform android
```

## Project Structure

```
party-decorator/
├── App.js                        # Root: navigation state, GestureHandler
├── app.json                      # Expo config (name, permissions, bundle IDs)
├── src/
│   ├── screens/
│   │   ├── HomeScreen.js         # Landing page + feature overview
│   │   └── DesignScreen.js       # Main design canvas + all controls
│   ├── components/
│   │   ├── DraggableItem.js      # Draggable, selectable decoration wrapper
│   │   ├── ColorPickerModal.js   # Bottom-sheet color picker (presets + hex)
│   │   └── ItemPalette.js        # Modal to select which item to add
│   └── decorations/
│       └── shapes.js             # SVG components for each decoration type
```

## How It Works

1. **Home screen** — tap "Create New Design"
2. **Design screen** — tap `+` to open the item palette and add a decoration
3. Drag it anywhere on the canvas
4. Tap the decoration to select it → use the context bar to:
   - Change its color
   - Bring it forward / send it backward
   - Delete it
5. Tap the `📸 Venue` button to upload a venue photo as the background
6. Tap `💾 Save` to export to camera roll, or `Share` to send to a client

## Roadmap

- Pinch-to-resize decorations
- Text labels & custom messages
- Gradient / pattern fills
- Multiple canvas templates (outdoor, ballroom, garden)
- Client presentation mode (full-screen view)
- Cloud save & design library
