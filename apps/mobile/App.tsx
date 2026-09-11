import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";

import { createApiClient } from "./src/api/client";
import { MobileConfigurationError, readMobileConfig } from "./src/config";
import {
  loadMarketplaceOverview,
  type MarketplaceOverview,
} from "./src/features/overview/service";

type ScreenState =
  | { status: "loading" }
  | { status: "ready"; data: MarketplaceOverview }
  | { status: "error"; message: string };

function configurationResult():
  | { ok: true; apiOrigin: string }
  | { ok: false; message: string } {
  try {
    return {
      ok: true,
      apiOrigin: readMobileConfig(process.env.EXPO_PUBLIC_API_URL).apiOrigin,
    };
  } catch (error) {
    return {
      ok: false,
      message:
        error instanceof MobileConfigurationError
          ? error.message
          : "Не удалось прочитать конфигурацию приложения",
    };
  }
}

export default function App() {
  const configuration = useMemo(() => configurationResult(), []);
  const [state, setState] = useState<ScreenState>({ status: "loading" });
  const client = useMemo(
    () => (configuration.ok ? createApiClient(configuration.apiOrigin) : null),
    [configuration],
  );

  const refresh = useCallback(async () => {
    if (!client) {
      setState({ status: "error", message: configuration.ok ? "API недоступен" : configuration.message });
      return;
    }
    setState({ status: "loading" });
    try {
      setState({ status: "ready", data: await loadMarketplaceOverview(client) });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Не удалось загрузить данные",
      });
    }
  }, [client, configuration]);

  useEffect(() => {
    let active = true;
    const initialLoad = client
      ? loadMarketplaceOverview(client)
      : Promise.reject(
          new Error(configuration.ok ? "API недоступен" : configuration.message),
        );
    void initialLoad
      .then((data) => {
        if (active) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "Не удалось загрузить данные",
          });
        }
      });
    return () => {
      active = false;
    };
  }, [client, configuration]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={state.status === "loading"} onRefresh={refresh} />}
      >
        <Text style={styles.eyebrow}>LAVA MOBILE LAB</Text>
        <Text style={styles.title}>Маркетплейс на телефоне</Text>
        <Text style={styles.lead}>
          Тестовый Expo-клиент использует тот же FastAPI и проверяет реальные контракты каталога.
        </Text>

        {state.status === "loading" && (
          <View style={styles.stateBox} accessibilityRole="progressbar">
            <ActivityIndicator color="#171717" />
            <Text>Подключаемся к API…</Text>
          </View>
        )}

        {state.status === "error" && (
          <View style={styles.errorBox} accessibilityLiveRegion="polite">
            <Text style={styles.errorTitle}>Нет подключения</Text>
            <Text style={styles.errorText}>{state.message}</Text>
            <Pressable style={styles.button} onPress={() => void refresh()} accessibilityRole="button">
              <Text style={styles.buttonText}>Повторить</Text>
            </Pressable>
          </View>
        )}

        {state.status === "ready" && (
          <>
            <View style={styles.statusCard}>
              <View>
                <Text style={styles.cardLabel}>API</Text>
                <Text style={styles.cardValue}>{state.data.service}</Text>
              </View>
              <Text style={styles.online}>Доступен</Text>
            </View>

            <Text style={styles.sectionTitle}>Категории</Text>
            <View style={styles.chips}>
              {state.data.categories.map((category) => (
                <View style={styles.chip} key={category.id}>
                  <Text style={styles.chipText}>{category.name}</Text>
                </View>
              ))}
            </View>

            <Text style={styles.sectionTitle}>Новые объявления</Text>
            <Text style={styles.muted}>Всего в поиске: {state.data.totalListings}</Text>
            {state.data.latestListings.length === 0 ? (
              <View style={styles.emptyBox}><Text>Активных объявлений пока нет.</Text></View>
            ) : state.data.latestListings.map((listing) => (
              <View style={styles.listingCard} key={listing.id}>
                <Text style={styles.listingTitle}>{listing.title}</Text>
                <Text style={styles.muted}>{listing.city}</Text>
                <Text style={styles.price}>
                  {listing.price === null ? "Цена по запросу" : `${listing.price} ₽`}
                </Text>
              </View>
            ))}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f4f1e9" },
  content: { padding: 24, paddingBottom: 48, gap: 16 },
  eyebrow: { fontSize: 12, fontWeight: "800", letterSpacing: 1.6, color: "#596b2d" },
  title: { fontSize: 38, lineHeight: 42, fontWeight: "800", color: "#171717" },
  lead: { fontSize: 17, lineHeight: 25, color: "#55534d" },
  stateBox: { minHeight: 160, alignItems: "center", justifyContent: "center", gap: 12 },
  errorBox: { padding: 20, gap: 12, borderWidth: 1, borderColor: "#d6846c", backgroundColor: "#fff7f3" },
  errorTitle: { fontSize: 20, fontWeight: "800", color: "#8a2f1f" },
  errorText: { fontSize: 15, lineHeight: 22, color: "#5f352c" },
  button: { alignSelf: "flex-start", paddingHorizontal: 18, paddingVertical: 12, backgroundColor: "#171717" },
  buttonText: { color: "#ffffff", fontWeight: "700" },
  statusCard: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 20, backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d8d4c8" },
  cardLabel: { fontSize: 12, color: "#77736b", textTransform: "uppercase" },
  cardValue: { marginTop: 4, fontSize: 18, fontWeight: "700", color: "#171717" },
  online: { paddingHorizontal: 10, paddingVertical: 6, backgroundColor: "#dff59e", color: "#34430e", fontWeight: "700" },
  sectionTitle: { marginTop: 12, fontSize: 24, fontWeight: "800", color: "#171717" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { paddingHorizontal: 13, paddingVertical: 9, borderRadius: 18, backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d8d4c8" },
  chipText: { color: "#2e2d29", fontWeight: "600" },
  muted: { color: "#77736b" },
  emptyBox: { padding: 20, backgroundColor: "#ebe7dc" },
  listingCard: { padding: 18, gap: 6, backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d8d4c8" },
  listingTitle: { fontSize: 18, fontWeight: "700", color: "#171717" },
  price: { marginTop: 6, fontSize: 20, fontWeight: "800", color: "#171717" },
});
