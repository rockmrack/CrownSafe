# Task 13: Localization Implementation Guide

## Multi-Language Support for BabyShield

---

## 1. API Integration

### Base Configuration

```javascript
// API Client Configuration
const API_BASE = 'https://babyshield.cureviax.ai';

class LocalizationManager {
  constructor() {
    this.currentLocale = 'en-US';
    this.translations = {};
    this.loadStoredLocale();
  }
  
  async loadStoredLocale() {
    // Load from storage
    const stored = await AsyncStorage.getItem('app_locale');
    if (stored) {
      this.currentLocale = stored;
    } else {
      // Detect device locale
      this.currentLocale = this.detectDeviceLocale();
    }
    
    // Load translations
    await this.loadTranslations();
  }
  
  detectDeviceLocale() {
    // iOS
    const iOSLocale = NativeModules.SettingsManager?.settings?.AppleLocale;
    
    // Android
    const androidLocale = NativeModules.I18nManager?.localeIdentifier;
    
    const deviceLocale = iOSLocale || androidLocale || 'en-US';
    
    // Map to supported locale
    return this.mapToSupportedLocale(deviceLocale);
  }
  
  mapToSupportedLocale(locale) {
    const supported = ['en-US', 'es-ES', 'es-MX'];
    
    // Exact match
    if (supported.includes(locale)) {
      return locale;
    }
    
    // Language match (es-* → es-ES)
    const lang = locale.split('-')[0];
    const match = supported.find(s => s.startsWith(lang));
    
    return match || 'en-US';
  }
  
  async loadTranslations() {
    try {
      const response = await fetch(`${API_BASE}/api/v1/i18n/translations?locale=${this.currentLocale}`);
      const data = await response.json();
      this.translations = data.translations;
    } catch (error) {
      console.error('Failed to load translations', error);
      // Fall back to embedded translations
      this.loadEmbeddedTranslations();
    }
  }
  
  t(key, params = {}) {
    let text = this.translations[key] || key;
    
    // Replace parameters
    Object.keys(params).forEach(param => {
      text = text.replace(`{${param}}`, params[param]);
    });
    
    return text;
  }
  
  async changeLocale(locale) {
    this.currentLocale = locale;
    await AsyncStorage.setItem('app_locale', locale);
    await this.loadTranslations();
    
    // Notify app of locale change
    EventEmitter.emit('localeChanged', locale);
  }
}

export const i18n = new LocalizationManager();
```

---

## 2. iOS Localization

### Project Setup

```bash
# Xcode project structure
BabyShield.xcodeproj/
  Localizations/
    en.lproj/
      Localizable.strings
      InfoPlist.strings
    es.lproj/
      Localizable.strings
      InfoPlist.strings
```

### Localizable.strings

```properties
/* en.lproj/Localizable.strings */

/* App */
"app.name" = "BabyShield";
"app.tagline" = "Scan or search recalled products. Instant safety info for families.";

/* Navigation */
"nav.home" = "Home";
"nav.scan" = "Scan";
"nav.search" = "Search";
"nav.alerts" = "Alerts";
"nav.settings" = "Settings";

/* Scanner */
"scanner.permission.title" = "Enable Camera for Barcode Scanning";
"scanner.permission.message" = "BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.";
"scanner.instruction" = "Point camera at product barcode";
"scanner.scanning" = "Scanning...";

/* Search */
"search.placeholder" = "Search for products or brands";
"search.button" = "Search";
"search.no_results" = "No results found";
"search.loading" = "Loading...";

/* Recalls */
"recall.found" = "⚠️ Recall Found!";
"recall.not_found" = "✅ No recalls found";
"recall.similar_found" = "No direct match—showing similar recalls";
"recall.safe_product" = "This product appears to be safe";

/* Accessibility */
"a11y.scan_button" = "Scan barcode button";
"a11y.search_button" = "Search button";
"a11y.back_button" = "Go back";
"a11y.close_button" = "Close";
```

```properties
/* es.lproj/Localizable.strings */

/* App */
"app.name" = "BabyShield";
"app.tagline" = "Escanea o busca productos retirados. Información de seguridad instantánea para familias.";

/* Navegación */
"nav.home" = "Inicio";
"nav.scan" = "Escanear";
"nav.search" = "Buscar";
"nav.alerts" = "Alertas";
"nav.settings" = "Configuración";

/* Escáner */
"scanner.permission.title" = "Habilitar Cámara para Escanear Códigos";
"scanner.permission.message" = "BabyShield necesita acceso a la cámara para escanear códigos de barras y verificar retiros de seguridad. No se almacenan fotos.";
"scanner.instruction" = "Apunta la cámara al código de barras";
"scanner.scanning" = "Escaneando...";

/* Búsqueda */
"search.placeholder" = "Buscar productos o marcas";
"search.button" = "Buscar";
"search.no_results" = "No se encontraron resultados";
"search.loading" = "Cargando...";

/* Retiros */
"recall.found" = "⚠️ ¡Retiro Encontrado!";
"recall.not_found" = "✅ No se encontraron retiros";
"recall.similar_found" = "Sin coincidencia directa—mostrando retiros similares";
"recall.safe_product" = "Este producto parece ser seguro";

/* Accesibilidad */
"a11y.scan_button" = "Botón escanear código de barras";
"a11y.search_button" = "Botón de búsqueda";
"a11y.back_button" = "Volver atrás";
"a11y.close_button" = "Cerrar";
```

### Swift Implementation

```swift
// Localization Extension
extension String {
    var localized: String {
        return NSLocalizedString(self, comment: "")
    }
    
    func localized(with arguments: CVarArg...) -> String {
        return String(format: self.localized, arguments: arguments)
    }
}

// Usage
titleLabel.text = "app.name".localized
subtitleLabel.text = "app.tagline".localized
scanButton.accessibilityLabel = "a11y.scan_button".localized

// With parameters
let count = 5
messageLabel.text = "search.results_count".localized(with: count)

// SwiftUI
struct LocalizedView: View {
    var body: some View {
        VStack {
            Text("app.name")
            Text("app.tagline")
            
            Button(action: scan) {
                Text("nav.scan")
            }
            .accessibilityLabel(Text("a11y.scan_button"))
        }
    }
}

// Dynamic locale switching
class LocalizationManager {
    static let shared = LocalizationManager()
    
    var currentLocale: Locale = .current {
        didSet {
            NotificationCenter.default.post(
                name: .localeChanged,
                object: nil
            )
        }
    }
    
    func setLocale(_ languageCode: String) {
        UserDefaults.standard.set([languageCode], forKey: "AppleLanguages")
        UserDefaults.standard.synchronize()
        
        // Restart app or reload UI
        currentLocale = Locale(identifier: languageCode)
    }
}
```

---

## 3. Android Localization

### Project Structure

```
app/src/main/res/
  values/
    strings.xml (default - en-US)
    colors.xml
    dimens.xml
  values-es/
    strings.xml (Spanish)
  values-es-rMX/
    strings.xml (Spanish - Mexico)
```

### strings.xml

```xml
<!-- res/values/strings.xml (English) -->
<resources>
    <!-- App -->
    <string name="app_name">BabyShield</string>
    <string name="app_tagline">Scan or search recalled products. Instant safety info for families.</string>
    
    <!-- Navigation -->
    <string name="nav_home">Home</string>
    <string name="nav_scan">Scan</string>
    <string name="nav_search">Search</string>
    <string name="nav_alerts">Alerts</string>
    <string name="nav_settings">Settings</string>
    
    <!-- Scanner -->
    <string name="scanner_permission_title">Enable Camera for Barcode Scanning</string>
    <string name="scanner_permission_message">BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.</string>
    <string name="scanner_instruction">Point camera at product barcode</string>
    <string name="scanner_scanning">Scanning…</string>
    
    <!-- Search -->
    <string name="search_placeholder">Search for products or brands</string>
    <string name="search_button">Search</string>
    <string name="search_no_results">No results found</string>
    <string name="search_loading">Loading…</string>
    
    <!-- Recalls -->
    <string name="recall_found">⚠️ Recall Found!</string>
    <string name="recall_not_found">✅ No recalls found</string>
    <string name="recall_similar_found">No direct match—showing similar recalls</string>
    <string name="recall_safe_product">This product appears to be safe</string>
    
    <!-- Plurals -->
    <plurals name="recall_count">
        <item quantity="zero">No recalls</item>
        <item quantity="one">%d recall</item>
        <item quantity="other">%d recalls</item>
    </plurals>
</resources>
```

```xml
<!-- res/values-es/strings.xml (Spanish) -->
<resources>
    <!-- App -->
    <string name="app_name">BabyShield</string>
    <string name="app_tagline">Escanea o busca productos retirados. Información de seguridad instantánea para familias.</string>
    
    <!-- Navegación -->
    <string name="nav_home">Inicio</string>
    <string name="nav_scan">Escanear</string>
    <string name="nav_search">Buscar</string>
    <string name="nav_alerts">Alertas</string>
    <string name="nav_settings">Configuración</string>
    
    <!-- Escáner -->
    <string name="scanner_permission_title">Habilitar Cámara para Escanear Códigos</string>
    <string name="scanner_permission_message">BabyShield necesita acceso a la cámara para escanear códigos de barras y verificar retiros de seguridad. No se almacenan fotos.</string>
    <string name="scanner_instruction">Apunta la cámara al código de barras</string>
    <string name="scanner_scanning">Escaneando…</string>
    
    <!-- Búsqueda -->
    <string name="search_placeholder">Buscar productos o marcas</string>
    <string name="search_button">Buscar</string>
    <string name="search_no_results">No se encontraron resultados</string>
    <string name="search_loading">Cargando…</string>
    
    <!-- Retiros -->
    <string name="recall_found">⚠️ ¡Retiro Encontrado!</string>
    <string name="recall_not_found">✅ No se encontraron retiros</string>
    <string name="recall_similar_found">Sin coincidencia directa—mostrando retiros similares</string>
    <string name="recall_safe_product">Este producto parece ser seguro</string>
    
    <!-- Plurales -->
    <plurals name="recall_count">
        <item quantity="zero">Sin retiros</item>
        <item quantity="one">%d retiro</item>
        <item quantity="other">%d retiros</item>
    </plurals>
</resources>
```

### Kotlin Implementation

```kotlin
// Localization in Activity
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Use string resources
        titleTextView.text = getString(R.string.app_name)
        subtitleTextView.text = getString(R.string.app_tagline)
        scanButton.contentDescription = getString(R.string.scanner_instruction)
        
        // With parameters
        val count = 5
        resultTextView.text = resources.getQuantityString(R.plurals.recall_count, count, count)
    }
}

// Jetpack Compose
@Composable
fun LocalizedScreen() {
    Column {
        Text(text = stringResource(R.string.app_name))
        Text(text = stringResource(R.string.app_tagline))
        
        Button(
            onClick = { scan() },
            modifier = Modifier.semantics {
                contentDescription = stringResource(R.string.scanner_instruction)
            }
        ) {
            Text(stringResource(R.string.nav_scan))
        }
        
        // Plurals
        val count = 5
        Text(
            text = pluralStringResource(R.plurals.recall_count, count, count)
        )
    }
}

// Dynamic locale switching
object LocaleManager {
    fun setLocale(context: Context, language: String): Context {
        val locale = Locale(language)
        Locale.setDefault(locale)
        
        val config = context.resources.configuration
        config.setLocale(locale)
        
        return context.createConfigurationContext(config)
    }
    
    fun persistLocale(context: Context, language: String) {
        val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
        prefs.edit().putString("app_locale", language).apply()
    }
    
    fun getPersistedLocale(context: Context): String {
        val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
        return prefs.getString("app_locale", "en") ?: "en"
    }
}

// Base Activity for locale handling
abstract class BaseActivity : AppCompatActivity() {
    override fun attachBaseContext(newBase: Context) {
        val language = LocaleManager.getPersistedLocale(newBase)
        val context = LocaleManager.setLocale(newBase, language)
        super.attachBaseContext(context)
    }
}
```

---

## 4. React Native Localization

### Setup

```bash
npm install react-native-localization
# or
yarn add react-native-localization
```

### Implementation

```javascript
// localization/index.js
import LocalizedStrings from 'react-native-localization';

const strings = new LocalizedStrings({
  'en-US': {
    app: {
      name: 'BabyShield',
      tagline: 'Scan or search recalled products. Instant safety info for families.'
    },
    nav: {
      home: 'Home',
      scan: 'Scan',
      search: 'Search',
      alerts: 'Alerts',
      settings: 'Settings'
    },
    scanner: {
      permissionTitle: 'Enable Camera for Barcode Scanning',
      permissionMessage: 'BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.',
      instruction: 'Point camera at product barcode',
      scanning: 'Scanning...'
    },
    search: {
      placeholder: 'Search for products or brands',
      button: 'Search',
      noResults: 'No results found',
      loading: 'Loading...'
    },
    recall: {
      found: '⚠️ Recall Found!',
      notFound: '✅ No recalls found',
      similarFound: 'No direct match—showing similar recalls',
      safeProduct: 'This product appears to be safe'
    },
    a11y: {
      scanButton: 'Scan barcode button',
      searchButton: 'Search button',
      backButton: 'Go back',
      closeButton: 'Close'
    }
  },
  'es-ES': {
    app: {
      name: 'BabyShield',
      tagline: 'Escanea o busca productos retirados. Información de seguridad instantánea para familias.'
    },
    nav: {
      home: 'Inicio',
      scan: 'Escanear',
      search: 'Buscar',
      alerts: 'Alertas',
      settings: 'Configuración'
    },
    scanner: {
      permissionTitle: 'Habilitar Cámara para Escanear Códigos',
      permissionMessage: 'BabyShield necesita acceso a la cámara para escanear códigos de barras y verificar retiros de seguridad. No se almacenan fotos.',
      instruction: 'Apunta la cámara al código de barras',
      scanning: 'Escaneando...'
    },
    search: {
      placeholder: 'Buscar productos o marcas',
      button: 'Buscar',
      noResults: 'No se encontraron resultados',
      loading: 'Cargando...'
    },
    recall: {
      found: '⚠️ ¡Retiro Encontrado!',
      notFound: '✅ No se encontraron retiros',
      similarFound: 'Sin coincidencia directa—mostrando retiros similares',
      safeProduct: 'Este producto parece ser seguro'
    },
    a11y: {
      scanButton: 'Botón escanear código de barras',
      searchButton: 'Botón de búsqueda',
      backButton: 'Volver atrás',
      closeButton: 'Cerrar'
    }
  }
});

export default strings;

// Usage in components
import strings from './localization';

function HomeScreen() {
  return (
    <View>
      <Text>{strings.app.name}</Text>
      <Text>{strings.app.tagline}</Text>
      
      <TouchableOpacity
        accessible={true}
        accessibilityLabel={strings.a11y.scanButton}
        onPress={handleScan}
      >
        <Text>{strings.nav.scan}</Text>
      </TouchableOpacity>
    </View>
  );
}

// Language switcher
function LanguageSettings() {
  const [locale, setLocale] = useState(strings.getLanguage());
  
  const changeLanguage = async (language) => {
    strings.setLanguage(language);
    await AsyncStorage.setItem('app_locale', language);
    setLocale(language);
    
    // Force re-render
    forceUpdate();
  };
  
  return (
    <View>
      <Text>{strings.settings.language}</Text>
      
      <TouchableOpacity onPress={() => changeLanguage('en-US')}>
        <Text>English</Text>
      </TouchableOpacity>
      
      <TouchableOpacity onPress={() => changeLanguage('es-ES')}>
        <Text>Español</Text>
      </TouchableOpacity>
    </View>
  );
}
```

---

## 5. Date & Number Formatting

### JavaScript/React Native

```javascript
// Date formatting
function formatDate(date, locale = 'en-US') {
  const options = {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  };
  
  return new Date(date).toLocaleDateString(locale, options);
}

// Number formatting
function formatNumber(number, locale = 'en-US') {
  return new Intl.NumberFormat(locale).format(number);
}

// Currency formatting
function formatCurrency(amount, locale = 'en-US', currency = 'USD') {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency
  }).format(amount);
}

// Usage
const recallDate = formatDate('2024-01-15', 'es-ES'); // "15 de enero de 2024"
const productCount = formatNumber(1500, 'es-ES'); // "1.500"
const price = formatCurrency(29.99, 'es-ES', 'EUR'); // "29,99 €"
```

### iOS

```swift
// Date formatting
let dateFormatter = DateFormatter()
dateFormatter.locale = Locale.current
dateFormatter.dateStyle = .long
let formattedDate = dateFormatter.string(from: recallDate)

// Number formatting
let numberFormatter = NumberFormatter()
numberFormatter.locale = Locale.current
numberFormatter.numberStyle = .decimal
let formattedNumber = numberFormatter.string(from: 1500)

// Currency formatting
let currencyFormatter = NumberFormatter()
currencyFormatter.locale = Locale.current
currencyFormatter.numberStyle = .currency
let formattedPrice = currencyFormatter.string(from: 29.99)
```

### Android

```kotlin
// Date formatting
val dateFormat = DateFormat.getDateInstance(DateFormat.LONG, Locale.getDefault())
val formattedDate = dateFormat.format(recallDate)

// Number formatting
val numberFormat = NumberFormat.getNumberInstance(Locale.getDefault())
val formattedNumber = numberFormat.format(1500)

// Currency formatting
val currencyFormat = NumberFormat.getCurrencyInstance(Locale.getDefault())
val formattedPrice = currencyFormat.format(29.99)
```

---

## 6. RTL Support (Future)

### iOS

```swift
// Info.plist
<key>CFBundleAllowMixedLocalizations</key>
<true/>

// Swift
if UIApplication.shared.userInterfaceLayoutDirection == .rightToLeft {
    // RTL specific layout
}

// SwiftUI
.environment(\.layoutDirection, .rightToLeft)
```

### Android

```xml
<!-- AndroidManifest.xml -->
<application
    android:supportsRtl="true">

<!-- Layout -->
<TextView
    android:layout_width="wrap_content"
    android:layout_height="wrap_content"
    android:textAlignment="viewStart"
    android:layout_marginStart="16dp"
    android:layout_marginEnd="16dp" />
```

---

## 7. Testing Localization

### Automated Tests

```javascript
// Jest test
describe('Localization', () => {
  test('English strings load correctly', () => {
    strings.setLanguage('en-US');
    expect(strings.app.name).toBe('BabyShield');
  });
  
  test('Spanish strings load correctly', () => {
    strings.setLanguage('es-ES');
    expect(strings.nav.home).toBe('Inicio');
  });
  
  test('Fallback to English for missing translations', () => {
    strings.setLanguage('fr-FR'); // Not supported
    expect(strings.getLanguage()).toBe('en-US');
  });
});
```

### Manual Testing Checklist

- [ ] All text displays in selected language
- [ ] Date formats match locale
- [ ] Number formats match locale  
- [ ] Currency displays correctly
- [ ] Text doesn't overflow or truncate
- [ ] Special characters display correctly
- [ ] Language switcher works
- [ ] Language preference persists
- [ ] API returns localized content
- [ ] Error messages are localized

---

## 8. Adding New Languages

### Steps

1. **API**: Add translations to `TRANSLATIONS` dict in `api/localization.py`
2. **iOS**: Add new `.lproj` folder with `Localizable.strings`
3. **Android**: Add new `values-XX` folder with `strings.xml`
4. **React Native**: Add new language object to `LocalizedStrings`
5. **Test**: Verify all screens and flows
6. **Update**: App store descriptions in new language

### Translation Keys Structure

```
app.*           - App level strings
nav.*           - Navigation items
scanner.*       - Barcode scanner
search.*        - Search functionality
recall.*        - Recall information
settings.*      - Settings screens
error.*         - Error messages
a11y.*          - Accessibility labels
action.*        - Action buttons
```

---

## 9. Best Practices

1. **Always use keys** - Never hardcode strings
2. **Provide context** - Add comments for translators
3. **Handle plurals** - Use proper plural forms
4. **Test text expansion** - Spanish ~30% longer than English
5. **Use native formatters** - For dates, numbers, currency
6. **Load translations async** - Don't block app startup
7. **Cache translations** - Reduce API calls
8. **Provide fallbacks** - Always have English backup
9. **Test with real devices** - Emulators may differ
10. **Get native review** - Have native speakers test

---

## 10. Localization Checklist

### Development

- [ ] All strings externalized
- [ ] Plurals handled correctly
- [ ] Date/time formatting
- [ ] Number formatting
- [ ] Currency formatting
- [ ] Images localized (if needed)
- [ ] API returns Accept-Language

### Testing

- [ ] Each language tested
- [ ] Text fits in UI
- [ ] Special characters work
- [ ] Switching languages works
- [ ] Persistence works
- [ ] Fallback works

### Deployment

- [ ] App store metadata translated
- [ ] Screenshots for each language
- [ ] Support documentation translated
- [ ] Privacy policy translated
- [ ] Terms of service translated
