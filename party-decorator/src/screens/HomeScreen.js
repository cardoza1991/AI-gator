import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const { width } = Dimensions.get('window');

const FEATURES = [
  {
    icon: '🎨',
    title: 'Drag & Drop Builder',
    desc: 'Place balloon arches, tables, backdrops, thrones & marquees on your canvas.',
  },
  {
    icon: '🌈',
    title: 'Full Color Control',
    desc: 'Tap any decoration and change its color instantly. 40+ presets or custom hex.',
  },
  {
    icon: '📸',
    title: 'Upload Your Venue',
    desc: 'Add a photo of the real space and design right on top of it for true-to-life mockups.',
  },
  {
    icon: '🧠',
    title: 'Layering System',
    desc: 'Bring items forward or send them back — stack balloons behind tables perfectly.',
  },
  {
    icon: '💾',
    title: 'Save & Share',
    desc: 'Export finished designs to your camera roll or share directly with clients.',
  },
];

export default function HomeScreen({ onNewDesign, savedDesigns = [] }) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      {/* Hero */}
      <View style={styles.hero}>
        <Text style={styles.heroTag}>EVENT DECORATION STUDIO</Text>
        <Text style={styles.heroTitle}>D•CORE</Text>
        <Text style={styles.heroSubtitle}>
          Design stunning party mockups for your clients in minutes — no design experience needed.
        </Text>
        <TouchableOpacity style={styles.ctaBtn} onPress={onNewDesign} activeOpacity={0.85}>
          <Text style={styles.ctaBtnText}>Create New Design</Text>
        </TouchableOpacity>
        {savedDesigns.length > 0 && (
          <Text style={styles.savedCount}>{savedDesigns.length} design{savedDesigns.length !== 1 ? 's' : ''} saved</Text>
        )}
      </View>

      {/* Feature list */}
      <ScrollView
        style={styles.featureScroll}
        contentContainerStyle={[styles.featureList, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.sectionTitle}>Everything You Need</Text>
        {FEATURES.map((f) => (
          <View key={f.title} style={styles.featureCard}>
            <Text style={styles.featureIcon}>{f.icon}</Text>
            <View style={styles.featureText}>
              <Text style={styles.featureTitle}>{f.title}</Text>
              <Text style={styles.featureDesc}>{f.desc}</Text>
            </View>
          </View>
        ))}

        {/* Quick-start CTA at bottom */}
        <TouchableOpacity
          style={styles.secondaryCta}
          onPress={onNewDesign}
          activeOpacity={0.85}
        >
          <Text style={styles.secondaryCtaText}>Start Designing →</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#F8F7FF',
  },
  hero: {
    backgroundColor: '#7C3AED',
    paddingHorizontal: 28,
    paddingTop: 32,
    paddingBottom: 36,
    alignItems: 'center',
    borderBottomLeftRadius: 32,
    borderBottomRightRadius: 32,
  },
  heroTag: {
    color: '#C4B5FD',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2.5,
    marginBottom: 8,
  },
  heroTitle: {
    color: '#FFFFFF',
    fontSize: 52,
    fontWeight: '900',
    letterSpacing: 6,
    marginBottom: 12,
  },
  heroSubtitle: {
    color: '#DDD6FE',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 28,
    maxWidth: width * 0.75,
  },
  ctaBtn: {
    backgroundColor: '#FBBF24',
    paddingHorizontal: 32,
    paddingVertical: 14,
    borderRadius: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  ctaBtnText: {
    color: '#1F2937',
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  savedCount: {
    color: '#C4B5FD',
    fontSize: 12,
    marginTop: 12,
  },
  featureScroll: {
    flex: 1,
  },
  featureList: {
    paddingHorizontal: 20,
    paddingTop: 24,
    gap: 14,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1F2937',
    marginBottom: 6,
  },
  featureCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    gap: 14,
    alignItems: 'flex-start',
    shadowColor: '#7C3AED',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  featureIcon: {
    fontSize: 28,
    marginTop: 2,
  },
  featureText: {
    flex: 1,
  },
  featureTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  featureDesc: {
    fontSize: 13,
    color: '#6B7280',
    lineHeight: 19,
  },
  secondaryCta: {
    backgroundColor: '#7C3AED',
    padding: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  secondaryCtaText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
