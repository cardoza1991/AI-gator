import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
} from 'react-native';

const PRESET_COLORS = [
  // Purples / Lavenders
  '#7C3AED', '#9333EA', '#C084FC', '#E9D5FF',
  // Pinks
  '#EC4899', '#F472B6', '#FBCFE8', '#BE185D',
  // Reds / Corals
  '#EF4444', '#F87171', '#FCA5A5', '#DC2626',
  // Oranges
  '#F97316', '#FB923C', '#FED7AA', '#EA580C',
  // Yellows / Golds
  '#F59E0B', '#FBBF24', '#FEF08A', '#D97706',
  // Greens
  '#10B981', '#34D399', '#A7F3D0', '#059669',
  // Blues
  '#3B82F6', '#60A5FA', '#BFDBFE', '#1D4ED8',
  // Teals
  '#06B6D4', '#22D3EE', '#A5F3FC', '#0891B2',
  // Neutrals
  '#FFFFFF', '#F8F7FF', '#6B7280', '#1F2937',
];

export default function ColorPickerModal({ visible, currentColor, onSelect, onClose }) {
  const [customHex, setCustomHex] = useState(currentColor || '#7C3AED');
  const [hexError, setHexError] = useState(false);

  const handleCustomApply = () => {
    const clean = customHex.startsWith('#') ? customHex : `#${customHex}`;
    if (/^#[0-9A-Fa-f]{6}$/.test(clean)) {
      setHexError(false);
      onSelect(clean);
    } else {
      setHexError(true);
    }
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.sheet} onPress={(e) => e.stopPropagation()}>
          <View style={styles.handle} />
          <Text style={styles.title}>Choose Color</Text>

          {/* Preset color grid */}
          <ScrollView contentContainerStyle={styles.grid} showsVerticalScrollIndicator={false}>
            {PRESET_COLORS.map((hex) => (
              <TouchableOpacity
                key={hex}
                style={[
                  styles.swatch,
                  { backgroundColor: hex },
                  currentColor === hex && styles.swatchSelected,
                  hex === '#FFFFFF' && styles.swatchBorder,
                ]}
                onPress={() => onSelect(hex)}
                activeOpacity={0.8}
              />
            ))}
          </ScrollView>

          {/* Custom hex input */}
          <View style={styles.hexRow}>
            <View style={[styles.hexPreview, { backgroundColor: customHex }]} />
            <TextInput
              style={[styles.hexInput, hexError && styles.hexInputError]}
              value={customHex}
              onChangeText={(t) => {
                setCustomHex(t);
                setHexError(false);
              }}
              placeholder="#C084FC"
              placeholderTextColor="#9CA3AF"
              maxLength={7}
              autoCapitalize="characters"
            />
            <TouchableOpacity style={styles.applyBtn} onPress={handleCustomApply}>
              <Text style={styles.applyBtnText}>Apply</Text>
            </TouchableOpacity>
          </View>
          {hexError && (
            <Text style={styles.hexErrorText}>Enter a valid hex code (e.g. #C084FC)</Text>
          )}

          <TouchableOpacity style={styles.closeBtn} onPress={onClose}>
            <Text style={styles.closeBtnText}>Done</Text>
          </TouchableOpacity>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  sheet: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: 20,
    paddingBottom: 32,
    paddingTop: 12,
    maxHeight: '70%',
  },
  handle: {
    width: 40,
    height: 4,
    backgroundColor: '#E5E7EB',
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 16,
    textAlign: 'center',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    paddingBottom: 16,
    justifyContent: 'flex-start',
  },
  swatch: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  swatchSelected: {
    borderWidth: 3,
    borderColor: '#7C3AED',
    transform: [{ scale: 1.15 }],
  },
  swatchBorder: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  hexRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 8,
    marginBottom: 4,
  },
  hexPreview: {
    width: 36,
    height: 36,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  hexInput: {
    flex: 1,
    height: 40,
    borderWidth: 1.5,
    borderColor: '#D1D5DB',
    borderRadius: 10,
    paddingHorizontal: 12,
    fontSize: 15,
    color: '#1F2937',
    fontFamily: 'monospace',
  },
  hexInputError: {
    borderColor: '#EF4444',
  },
  hexErrorText: {
    color: '#EF4444',
    fontSize: 12,
    marginBottom: 8,
    marginLeft: 46,
  },
  applyBtn: {
    backgroundColor: '#7C3AED',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 10,
  },
  applyBtnText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
  closeBtn: {
    marginTop: 12,
    backgroundColor: '#F3F4F6',
    padding: 14,
    borderRadius: 14,
    alignItems: 'center',
  },
  closeBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
});
