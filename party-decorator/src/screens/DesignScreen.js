import React, { useRef, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
  Dimensions,
  Image,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import ViewShot from 'react-native-view-shot';
import DraggableItem from '../components/DraggableItem';
import ColorPickerModal from '../components/ColorPickerModal';
import ItemPalette from '../components/ItemPalette';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CANVAS_HEIGHT = SCREEN_WIDTH * 1.25; // 4:5 aspect

let nextId = 1;

function makeItem(catalogEntry, canvasWidth, canvasHeight) {
  const id = `item_${nextId++}`;
  return {
    id,
    type: catalogEntry.type,
    color: catalogEntry.defaultColor,
    width: catalogEntry.defaultWidth,
    height: catalogEntry.defaultHeight,
    x: Math.max(0, (canvasWidth - catalogEntry.defaultWidth) / 2),
    y: Math.max(0, (canvasHeight - catalogEntry.defaultHeight) / 2),
    zIndex: nextId,
  };
}

export default function DesignScreen({ onBack, onSave }) {
  const insets = useSafeAreaInsets();
  const canvasRef = useRef(null);
  const canvasWidth = SCREEN_WIDTH;

  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [backgroundUri, setBackgroundUri] = useState(null);
  const [showPalette, setShowPalette] = useState(false);
  const [showColorPicker, setShowColorPicker] = useState(false);

  const selectedItem = items.find((i) => i.id === selectedId) || null;

  // ── Item manipulation ──────────────────────────────────────────

  const addItem = useCallback((catalogEntry) => {
    const newItem = makeItem(catalogEntry, canvasWidth, CANVAS_HEIGHT);
    setItems((prev) => [...prev, newItem]);
    setSelectedId(newItem.id);
  }, [canvasWidth]);

  const updatePosition = useCallback((id, x, y) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, x, y } : item))
    );
  }, []);

  const updateColor = useCallback((id, color) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, color } : item))
    );
  }, []);

  const deleteSelected = useCallback(() => {
    if (!selectedId) return;
    setItems((prev) => prev.filter((i) => i.id !== selectedId));
    setSelectedId(null);
  }, [selectedId]);

  const bringForward = useCallback(() => {
    if (!selectedId) return;
    setItems((prev) =>
      prev.map((item) =>
        item.id === selectedId ? { ...item, zIndex: item.zIndex + 1 } : item
      )
    );
  }, [selectedId]);

  const sendBackward = useCallback(() => {
    if (!selectedId) return;
    setItems((prev) =>
      prev.map((item) =>
        item.id === selectedId
          ? { ...item, zIndex: Math.max(0, item.zIndex - 1) }
          : item
      )
    );
  }, [selectedId]);

  // ── Background photo ───────────────────────────────────────────

  const pickVenuePhoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        'Permission needed',
        'Please allow photo library access in your device settings.'
      );
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 5],
      quality: 0.85,
    });
    if (!result.canceled && result.assets.length > 0) {
      setBackgroundUri(result.assets[0].uri);
    }
  };

  const clearBackground = () => setBackgroundUri(null);

  // ── Save / Share ───────────────────────────────────────────────

  const captureCanvas = async () => {
    if (!canvasRef.current) return null;
    try {
      const uri = await canvasRef.current.capture();
      return uri;
    } catch (e) {
      console.error('Capture failed', e);
      return null;
    }
  };

  const handleSave = async () => {
    const uri = await captureCanvas();
    if (!uri) {
      Alert.alert('Error', 'Could not capture design.');
      return;
    }
    if (Platform.OS !== 'web') {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status === 'granted') {
        await MediaLibrary.saveToLibraryAsync(uri);
        Alert.alert('Saved!', 'Your design has been saved to Photos.');
        onSave?.({ uri, timestamp: Date.now() });
      } else {
        Alert.alert('Permission needed', 'Allow access to save to Photos.');
      }
    } else {
      Alert.alert('Saved!', 'Design captured.');
    }
  };

  const handleShare = async () => {
    const uri = await captureCanvas();
    if (!uri) {
      Alert.alert('Error', 'Could not capture design.');
      return;
    }
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(uri, {
        mimeType: 'image/png',
        dialogTitle: 'Share your party design',
      });
    } else {
      Alert.alert('Sharing not available', 'Cannot share on this device.');
    }
  };

  // ── Deselect on canvas tap ─────────────────────────────────────

  const handleCanvasTap = () => setSelectedId(null);

  // ── Render ────────────────────────────────────────────────────

  const sortedItems = [...items].sort((a, b) => a.zIndex - b.zIndex);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.headerBtn}>
          <Text style={styles.headerBtnText}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>D•CORE</Text>
        <TouchableOpacity onPress={handleShare} style={styles.headerBtnPrimary}>
          <Text style={styles.headerBtnPrimaryText}>Share</Text>
        </TouchableOpacity>
      </View>

      {/* Canvas */}
      <View style={styles.canvasWrapper}>
        <ViewShot
          ref={canvasRef}
          options={{ format: 'png', quality: 1 }}
          style={[styles.canvas, { width: canvasWidth, height: CANVAS_HEIGHT }]}
        >
          {/* Background */}
          <TouchableOpacity
            activeOpacity={1}
            onPress={handleCanvasTap}
            style={StyleSheet.absoluteFill}
          >
            {backgroundUri ? (
              <Image
                source={{ uri: backgroundUri }}
                style={StyleSheet.absoluteFill}
                resizeMode="cover"
              />
            ) : (
              <View style={styles.blankCanvas}>
                <Text style={styles.canvasHint}>
                  Tap "+" to add decorations{'\n'}or upload your venue photo
                </Text>
              </View>
            )}
          </TouchableOpacity>

          {/* Decoration items */}
          {sortedItems.map((item) => (
            <DraggableItem
              key={item.id}
              item={item}
              isSelected={item.id === selectedId}
              onPositionChange={updatePosition}
              onPress={setSelectedId}
            />
          ))}
        </ViewShot>
      </View>

      {/* Context toolbar (shown when item is selected) */}
      {selectedItem && (
        <View style={styles.contextBar}>
          <TouchableOpacity
            style={styles.ctxBtn}
            onPress={() => setShowColorPicker(true)}
          >
            <View style={[styles.colorDot, { backgroundColor: selectedItem.color }]} />
            <Text style={styles.ctxBtnText}>Color</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.ctxBtn} onPress={bringForward}>
            <Text style={styles.ctxBtnIcon}>↑</Text>
            <Text style={styles.ctxBtnText}>Forward</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.ctxBtn} onPress={sendBackward}>
            <Text style={styles.ctxBtnIcon}>↓</Text>
            <Text style={styles.ctxBtnText}>Backward</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.ctxBtn, styles.ctxBtnDelete]}
            onPress={deleteSelected}
          >
            <Text style={styles.ctxBtnIconDelete}>✕</Text>
            <Text style={[styles.ctxBtnText, styles.ctxBtnDeleteText]}>Remove</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Bottom toolbar */}
      <View style={[styles.toolbar, { paddingBottom: insets.bottom + 8 }]}>
        {/* Left group */}
        <View style={styles.toolbarGroup}>
          <TouchableOpacity style={styles.toolBtn} onPress={pickVenuePhoto}>
            <Text style={styles.toolBtnIcon}>📸</Text>
            <Text style={styles.toolBtnText}>Venue</Text>
          </TouchableOpacity>
          {backgroundUri && (
            <TouchableOpacity style={styles.toolBtn} onPress={clearBackground}>
              <Text style={styles.toolBtnIcon}>🗑</Text>
              <Text style={styles.toolBtnText}>Clear BG</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Centre: Add item */}
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setShowPalette(true)}
          activeOpacity={0.85}
        >
          <Text style={styles.addBtnText}>+</Text>
        </TouchableOpacity>

        {/* Right group */}
        <View style={styles.toolbarGroup}>
          <TouchableOpacity style={styles.toolBtn} onPress={handleSave}>
            <Text style={styles.toolBtnIcon}>💾</Text>
            <Text style={styles.toolBtnText}>Save</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Modals */}
      <ItemPalette
        visible={showPalette}
        onSelect={addItem}
        onClose={() => setShowPalette(false)}
      />

      <ColorPickerModal
        visible={showColorPicker}
        currentColor={selectedItem?.color}
        onSelect={(color) => {
          if (selectedId) updateColor(selectedId, color);
          setShowColorPicker(false);
        }}
        onClose={() => setShowColorPicker(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#1F2937',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#111827',
  },
  headerBtn: {
    padding: 8,
  },
  headerBtnText: {
    color: '#D1D5DB',
    fontSize: 15,
    fontWeight: '500',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: 2,
  },
  headerBtnPrimary: {
    backgroundColor: '#7C3AED',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  headerBtnPrimaryText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  canvasWrapper: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#374151',
  },
  canvas: {
    backgroundColor: '#FFFFFF',
    overflow: 'hidden',
  },
  blankCanvas: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F9FAFB',
  },
  canvasHint: {
    color: '#9CA3AF',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
  },
  contextBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    backgroundColor: '#111827',
    paddingVertical: 8,
    paddingHorizontal: 12,
    gap: 4,
  },
  ctxBtn: {
    alignItems: 'center',
    flex: 1,
    paddingVertical: 6,
    borderRadius: 10,
    backgroundColor: '#1F2937',
    gap: 2,
  },
  ctxBtnDelete: {
    backgroundColor: '#450A0A',
  },
  ctxBtnIcon: {
    fontSize: 16,
    color: '#E5E7EB',
  },
  ctxBtnIconDelete: {
    fontSize: 16,
    color: '#FCA5A5',
  },
  ctxBtnText: {
    fontSize: 10,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  ctxBtnDeleteText: {
    color: '#FCA5A5',
  },
  colorDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#111827',
    paddingHorizontal: 24,
    paddingTop: 12,
  },
  toolbarGroup: {
    flexDirection: 'row',
    gap: 8,
  },
  toolBtn: {
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: 8,
  },
  toolBtnIcon: {
    fontSize: 22,
  },
  toolBtnText: {
    fontSize: 10,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  addBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#7C3AED',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#7C3AED',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.5,
    shadowRadius: 8,
    elevation: 8,
    marginTop: -20,
  },
  addBtnText: {
    color: '#FFFFFF',
    fontSize: 30,
    fontWeight: '300',
    lineHeight: 34,
  },
});
