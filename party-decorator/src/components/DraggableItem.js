import React, { useRef } from 'react';
import {
  Animated,
  PanResponder,
  TouchableOpacity,
  View,
  StyleSheet,
} from 'react-native';
import { getComponentByType } from '../decorations/shapes';

/**
 * A single draggable decoration on the canvas.
 *
 * Props:
 *  item           – { id, type, x, y, color, zIndex, width, height }
 *  isSelected     – boolean
 *  onSelect       – (id) => void
 *  onPositionChange – (id, newX, newY) => void
 *  onPress        – (id) => void  (tap without drag → show controls)
 */
export default function DraggableItem({
  item,
  isSelected,
  onPositionChange,
  onPress,
}) {
  const pan = useRef(new Animated.ValueXY()).current;
  const isDragging = useRef(false);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: (_, gs) =>
        Math.abs(gs.dx) > 4 || Math.abs(gs.dy) > 4,

      onPanResponderGrant: () => {
        pan.setValue({ x: 0, y: 0 });
        isDragging.current = false;
      },

      onPanResponderMove: (_, gs) => {
        isDragging.current = true;
        pan.setValue({ x: gs.dx, y: gs.dy });
      },

      onPanResponderRelease: (_, gs) => {
        if (!isDragging.current) {
          // It was a tap
          pan.setValue({ x: 0, y: 0 });
          return;
        }
        // Commit position
        const newX = item.x + gs.dx;
        const newY = item.y + gs.dy;
        pan.setValue({ x: 0, y: 0 });
        onPositionChange(item.id, newX, newY);
      },
    })
  ).current;

  const DecorationComponent = getComponentByType(item.type);

  return (
    <Animated.View
      style={[
        styles.container,
        {
          left: item.x,
          top: item.y,
          zIndex: item.zIndex,
          width: item.width,
          height: item.height,
          transform: [{ translateX: pan.x }, { translateY: pan.y }],
        },
        isSelected && styles.selectedBorder,
      ]}
      {...panResponder.panHandlers}
    >
      <TouchableOpacity
        activeOpacity={0.9}
        onPress={() => onPress(item.id)}
        style={{ width: item.width, height: item.height }}
      >
        {DecorationComponent ? (
          <DecorationComponent
            color={item.color}
            width={item.width}
            height={item.height}
          />
        ) : null}
      </TouchableOpacity>

      {/* Selection handles */}
      {isSelected && (
        <>
          <View style={[styles.handle, styles.handleTL]} />
          <View style={[styles.handle, styles.handleTR]} />
          <View style={[styles.handle, styles.handleBL]} />
          <View style={[styles.handle, styles.handleBR]} />
        </>
      )}
    </Animated.View>
  );
}

const HANDLE_SIZE = 10;

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
  },
  selectedBorder: {
    borderWidth: 2,
    borderColor: '#7C3AED',
    borderStyle: 'dashed',
    borderRadius: 4,
  },
  handle: {
    position: 'absolute',
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
    borderRadius: HANDLE_SIZE / 2,
    backgroundColor: '#7C3AED',
    borderWidth: 2,
    borderColor: '#FFFFFF',
  },
  handleTL: { top: -HANDLE_SIZE / 2, left: -HANDLE_SIZE / 2 },
  handleTR: { top: -HANDLE_SIZE / 2, right: -HANDLE_SIZE / 2 },
  handleBL: { bottom: -HANDLE_SIZE / 2, left: -HANDLE_SIZE / 2 },
  handleBR: { bottom: -HANDLE_SIZE / 2, right: -HANDLE_SIZE / 2 },
});
