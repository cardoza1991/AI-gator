import 'react-native-gesture-handler';
import React, { useState } from 'react';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import HomeScreen from './src/screens/HomeScreen';
import DesignScreen from './src/screens/DesignScreen';

export default function App() {
  const [screen, setScreen] = useState('home');
  const [savedDesigns, setSavedDesigns] = useState([]);

  const handleSaveDesign = (design) => {
    setSavedDesigns((prev) => [design, ...prev]);
  };

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="light" />
        {screen === 'home' ? (
          <HomeScreen
            onNewDesign={() => setScreen('design')}
            savedDesigns={savedDesigns}
          />
        ) : (
          <DesignScreen
            onBack={() => setScreen('home')}
            onSave={handleSaveDesign}
          />
        )}
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
