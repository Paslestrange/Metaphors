import { Stack } from 'expo-router';
import { View, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: '#0a0a1a',
          },
          headerTintColor: '#e0e0e0',
          headerTitleStyle: {
            fontWeight: '600',
          },
          contentStyle: {
            backgroundColor: '#0a0a1a',
          },
          animation: 'fade',
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            headerShown: false,
          }}
        />
        <Stack.Screen
          name="about"
          options={{
            title: 'About',
          }}
        />
        <Stack.Screen
          name="+not-found"
          options={{
            title: 'Not Found',
            presentation: 'modal',
          }}
        />
      </Stack>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a1a',
  },
});
