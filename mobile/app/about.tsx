import { ScrollView, View, Text, StyleSheet, Linking, TouchableOpacity } from 'react-native';
import { Stack } from 'expo-router';

const SECTION_COLOR = '#8b5cf6';
const TEXT_COLOR = '#e0e0e0';
const MUTED_COLOR = '#9ca3af';
const BG_COLOR = '#0a0a1a';
const CARD_BG = '#12122a';

export default function AboutScreen() {
  const openLink = (url: string) => {
    Linking.openURL(url).catch(() => {});
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: 'About',
          headerStyle: { backgroundColor: BG_COLOR },
          headerTintColor: TEXT_COLOR,
          headerTitleStyle: { fontWeight: '600' },
        }}
      />
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* App Info */}
        <View style={styles.header}>
          <Text style={styles.appName}>Metaphors</Text>
          <Text style={styles.tagline}>Infrastructure Visualization</Text>
          <Text style={styles.version}>Version 1.0.0</Text>
        </View>

        {/* About */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>
          <Text style={styles.body}>
            Metaphors is an open-source infrastructure visualization platform that renders
            complex workloads as interactive 3D environments. Not a monitoring replacement —
            a visualization layer that sits on top of existing data sources (Prometheus,
            Datadog, Kubernetes) and makes infrastructure instantly legible.
          </Text>
          <Text style={styles.body}>
            You don't read "service X is degraded" — you see a building flickering in the city.
            You don't parse "pod restart count is high" — you see a room's lights switching
            on and off.
          </Text>
        </View>

        {/* Impressum */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Impressum</Text>
          <Text style={styles.body}>
            Pascal Stange{'\n'}
            Metaphors Project{'\n'}
            Open Source — GitHub Repository
          </Text>
          <TouchableOpacity onPress={() => openLink('https://github.com/metaphors-io/metaphors')}>
            <Text style={styles.link}>github.com/metaphors-io/metaphors</Text>
          </TouchableOpacity>
        </View>

        {/* Datenschutz */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Datenschutz</Text>
          <Text style={styles.body}>
            This app collects minimal data required for operation:{'\n'}
            {'\n'}
            • Location (optional) — used only to display nearby infrastructure metrics when
            explicitly enabled by the user.{'\n'}
            {'\n'}
            • Connection data — the app connects to your self-hosted Metaphors server
            instance. No data is sent to third-party servers.{'\n'}
            {'\n'}
            • No analytics, no tracking, no advertising.{'\n'}
            {'\n'}
            All infrastructure data stays between this app and your own server. We do not
            store, process, or forward any of your monitoring data.
          </Text>
        </View>

        {/* Open Source */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Open Source</Text>
          <Text style={styles.body}>
            Metaphors is released under the MIT License. Contributions welcome.
          </Text>
          <TouchableOpacity onPress={() => openLink('https://github.com/metaphors-io/metaphors/blob/main/LICENSE')}>
            <Text style={styles.link}>View License</Text>
          </TouchableOpacity>
        </View>

        {/* Links */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Links</Text>
          <TouchableOpacity style={styles.linkRow} onPress={() => openLink('https://github.com/metaphors-io/metaphors')}>
            <Text style={styles.link}>GitHub Repository</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkRow} onPress={() => openLink('https://github.com/metaphors-io/metaphors/issues')}>
            <Text style={styles.link}>Report an Issue</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.linkRow} onPress={() => openLink('https://metaphors.io')}>
            <Text style={styles.link}>Website</Text>
          </TouchableOpacity>
        </View>

        <Text style={styles.footer}>© 2026 Metaphors Contributors</Text>
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: BG_COLOR,
  },
  content: {
    padding: 20,
    paddingTop: 16,
    paddingBottom: 40,
  },
  header: {
    alignItems: 'center',
    marginBottom: 28,
    paddingTop: 8,
  },
  appName: {
    fontSize: 28,
    fontWeight: '700',
    color: SECTION_COLOR,
    letterSpacing: 0.5,
  },
  tagline: {
    fontSize: 14,
    color: MUTED_COLOR,
    marginTop: 4,
  },
  version: {
    fontSize: 12,
    color: MUTED_COLOR,
    marginTop: 6,
    opacity: 0.7,
  },
  section: {
    backgroundColor: CARD_BG,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: SECTION_COLOR,
    marginBottom: 10,
  },
  body: {
    fontSize: 14,
    color: TEXT_COLOR,
    lineHeight: 21,
  },
  link: {
    fontSize: 14,
    color: SECTION_COLOR,
    marginTop: 8,
    textDecorationLine: 'underline',
  },
  linkRow: {
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#1e1e3a',
  },
  footer: {
    textAlign: 'center',
    fontSize: 12,
    color: MUTED_COLOR,
    marginTop: 16,
    opacity: 0.6,
  },
});
