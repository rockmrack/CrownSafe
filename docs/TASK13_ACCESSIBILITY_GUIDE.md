# Task 13: Mobile Accessibility Implementation Guide

## WCAG AA Compliance Requirements

---

## 1. Dynamic Type Support

### iOS Implementation

```swift
// Enable Dynamic Type support
class AccessibleViewController: UIViewController {
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        // Listen for content size changes
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(contentSizeDidChange),
            name: UIContentSizeCategory.didChangeNotification,
            object: nil
        )
        
        setupDynamicType()
    }
    
    func setupDynamicType() {
        // Use system text styles
        titleLabel.font = UIFont.preferredFont(forTextStyle: .title1)
        titleLabel.adjustsFontForContentSizeCategory = true
        titleLabel.numberOfLines = 0
        
        bodyLabel.font = UIFont.preferredFont(forTextStyle: .body)
        bodyLabel.adjustsFontForContentSizeCategory = true
        bodyLabel.numberOfLines = 0
        
        // Custom font with Dynamic Type
        let customFont = UIFont(name: "CustomFont", size: 17)!
        let metrics = UIFontMetrics(forTextStyle: .body)
        bodyLabel.font = metrics.scaledFont(for: customFont)
        
        // Minimum and maximum scaling
        bodyLabel.minimumScaleFactor = 0.85
        bodyLabel.adjustsFontSizeToFitWidth = true
    }
    
    @objc func contentSizeDidChange() {
        // Update layout for new text size
        view.setNeedsLayout()
        tableView?.reloadData()
    }
}

// SwiftUI Dynamic Type
struct AccessibleView: View {
    @Environment(\.sizeCategory) var sizeCategory
    
    var body: some View {
        VStack {
            Text("Scalable Title")
                .font(.largeTitle)
                .minimumScaleFactor(0.7)
                .lineLimit(nil)
            
            Text("Body text that scales")
                .font(.body)
            
            // Conditional layout based on text size
            if sizeCategory.isAccessibilityCategory {
                // Stack vertically for large text
                VStack {
                    Button("Action 1") {}
                    Button("Action 2") {}
                }
            } else {
                // Side by side for normal text
                HStack {
                    Button("Action 1") {}
                    Button("Action 2") {}
                }
            }
        }
    }
}
```

### Android Implementation

```kotlin
// Enable Dynamic Type in Android
class AccessibleActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Respect system font scale
        val fontScale = resources.configuration.fontScale
        
        // Use sp units for text (scales with system setting)
        titleTextView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 24f)
        bodyTextView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
        
        // Handle extreme text scaling
        if (fontScale > 1.3f) {
            // Adjust layout for large text
            switchToVerticalLayout()
        }
    }
    
    private fun setupScalableText() {
        // Material Design type system with scaling
        titleTextView.setTextAppearance(R.style.TextAppearance_MaterialComponents_Headline4)
        bodyTextView.setTextAppearance(R.style.TextAppearance_MaterialComponents_Body1)
        
        // Auto-sizing TextView
        TextViewCompat.setAutoSizeTextTypeWithDefaults(
            titleTextView,
            TextViewCompat.AUTO_SIZE_TEXT_TYPE_UNIFORM
        )
        
        TextViewCompat.setAutoSizeTextTypeUniformWithConfiguration(
            bodyTextView,
            12, // min size in sp
            20, // max size in sp
            1,  // step
            TypedValue.COMPLEX_UNIT_SP
        )
    }
}

// Jetpack Compose
@Composable
fun AccessibleScreen() {
    val configuration = LocalConfiguration.current
    val fontScale = configuration.fontScale
    
    Column {
        Text(
            text = "Scalable Title",
            style = MaterialTheme.typography.h4.copy(
                fontSize = (24 * fontScale).sp
            ),
            maxLines = Int.MAX_VALUE
        )
        
        // Responsive layout based on font scale
        if (fontScale > 1.3f) {
            // Vertical layout for large text
            Column {
                Button(onClick = {}) { Text("Action 1") }
                Button(onClick = {}) { Text("Action 2") }
            }
        } else {
            // Horizontal layout for normal text
            Row {
                Button(onClick = {}) { Text("Action 1") }
                Button(onClick = {}) { Text("Action 2") }
            }
        }
    }
}
```

---

## 2. Color Contrast Requirements

### WCAG AA Standards
- **Normal text**: 4.5:1 contrast ratio
- **Large text** (18pt+ or 14pt+ bold): 3:1 contrast ratio
- **UI elements**: 3:1 contrast ratio

### Color Palette

```swift
// iOS Color Extension
extension UIColor {
    static let accessibleColors = AccessibleColors()
    
    struct AccessibleColors {
        // Primary colors with AA compliance
        let primary = UIColor(hex: "#0066CC")      // 5.48:1 on white
        let primaryText = UIColor.white            // Use on primary
        
        let danger = UIColor(hex: "#CC0000")       // 5.91:1 on white
        let dangerText = UIColor.white             // Use on danger
        
        let success = UIColor(hex: "#008800")      // 5.14:1 on white
        let successText = UIColor.white            // Use on success
        
        // Text colors
        let primaryTextColor = UIColor(hex: "#212121")    // 15.8:1 on white
        let secondaryTextColor = UIColor(hex: "#666666")  // 5.74:1 on white
        let disabledTextColor = UIColor(hex: "#9E9E9E")   // 3.03:1 on white (AA for large text only)
        
        // Background colors
        let backgroundColor = UIColor.white
        let surfaceColor = UIColor(hex: "#F5F5F5")
        let dividerColor = UIColor(hex: "#E0E0E0")
    }
    
    // Check contrast ratio
    func contrastRatio(with backgroundColor: UIColor) -> CGFloat {
        let l1 = self.luminance()
        let l2 = backgroundColor.luminance()
        
        let lighter = max(l1, l2)
        let darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    }
    
    func meetsWCAG_AA(backgroundColor: UIColor, isLargeText: Bool = false) -> Bool {
        let ratio = contrastRatio(with: backgroundColor)
        return isLargeText ? ratio >= 3.0 : ratio >= 4.5
    }
}
```

```kotlin
// Android Color Resources
// res/values/colors.xml
<resources>
    <!-- WCAG AA Compliant Colors -->
    <color name="primary">#0066CC</color>           <!-- 5.48:1 on white -->
    <color name="primary_text">#FFFFFF</color>
    
    <color name="danger">#CC0000</color>            <!-- 5.91:1 on white -->
    <color name="danger_text">#FFFFFF</color>
    
    <color name="success">#008800</color>           <!-- 5.14:1 on white -->
    <color name="success_text">#FFFFFF</color>
    
    <!-- Text Colors -->
    <color name="text_primary">#212121</color>      <!-- 15.8:1 on white -->
    <color name="text_secondary">#666666</color>    <!-- 5.74:1 on white -->
    <color name="text_disabled">#9E9E9E</color>     <!-- 3.03:1 (large text only) -->
    
    <!-- Background Colors -->
    <color name="background">#FFFFFF</color>
    <color name="surface">#F5F5F5</color>
    <color name="divider">#E0E0E0</color>
</resources>

// Contrast checking utility
object ContrastChecker {
    fun checkContrast(foreground: Int, background: Int): Double {
        val l1 = ColorUtils.calculateLuminance(foreground)
        val l2 = ColorUtils.calculateLuminance(background)
        
        val lighter = max(l1, l2)
        val darker = min(l1, l2)
        
        return (lighter + 0.05) / (darker + 0.05)
    }
    
    fun meetsWCAG_AA(foreground: Int, background: Int, isLargeText: Boolean = false): Boolean {
        val ratio = checkContrast(foreground, background)
        return if (isLargeText) ratio >= 3.0 else ratio >= 4.5
    }
}
```

---

## 3. VoiceOver/TalkBack Labels

### iOS VoiceOver

```swift
// Basic accessibility labels
button.accessibilityLabel = "Scan barcode"
button.accessibilityHint = "Double tap to open camera and scan a product barcode"
button.accessibilityTraits = .button

// Custom views
class RecallCard: UIView {
    override var isAccessibilityElement: Bool {
        get { true }
        set {}
    }
    
    override var accessibilityLabel: String? {
        get {
            return "\(productName), \(brand). Recall: \(hazard). \(remedyAction)"
        }
        set {}
    }
    
    override var accessibilityTraits: UIAccessibilityTraits {
        get { [.button] }
        set {}
    }
    
    override var accessibilityValue: String? {
        get {
            return isExpanded ? "Expanded" : "Collapsed"
        }
        set {}
    }
}

// Grouped elements
containerView.shouldGroupAccessibilityChildren = true

// Live regions for dynamic content
resultLabel.accessibilityTraits = [.updatesFrequently]

// Custom actions
override var accessibilityCustomActions: [UIAccessibilityCustomAction]? {
    get {
        return [
            UIAccessibilityCustomAction(
                name: "View Details",
                target: self,
                selector: #selector(viewDetails)
            ),
            UIAccessibilityCustomAction(
                name: "Share",
                target: self,
                selector: #selector(share)
            )
        ]
    }
    set {}
}

// Announcements
UIAccessibility.post(
    notification: .announcement,
    argument: "Recall found for this product"
)
```

### Android TalkBack

```kotlin
// Basic content descriptions
scanButton.contentDescription = "Scan barcode"
scanButton.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES

// Custom views
class RecallCard : CardView {
    init {
        // Make the entire card clickable and accessible
        isFocusable = true
        isClickable = true
        
        contentDescription = buildContentDescription()
        
        // Add custom actions
        ViewCompat.addAccessibilityAction(
            this,
            "View Details"
        ) { _, _ ->
            viewDetails()
            true
        }
    }
    
    private fun buildContentDescription(): String {
        return "$productName, $brand. Recall: $hazard. $remedyAction"
    }
    
    fun updateAccessibilityState(isExpanded: Boolean) {
        ViewCompat.setStateDescription(
            this,
            if (isExpanded) "Expanded" else "Collapsed"
        )
    }
}

// Group related elements
parentLayout.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_YES
ViewCompat.setScreenReaderFocusable(parentLayout, true)

// Live regions for dynamic content
resultTextView.accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE

// Announcements
resultTextView.announceForAccessibility("Recall found for this product")

// Role descriptions
ViewCompat.setRoleDescription(customButton, "Search button")
```

### React Native

```javascript
// Accessibility props
<TouchableOpacity
  accessible={true}
  accessibilityLabel="Scan barcode"
  accessibilityHint="Double tap to open camera and scan a product barcode"
  accessibilityRole="button"
  accessibilityState={{ disabled: false }}
  onPress={handleScan}
>
  <Text>Scan</Text>
</TouchableOpacity>

// Custom component
function RecallCard({ recall }) {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <TouchableOpacity
      accessible={true}
      accessibilityLabel={`${recall.productName}, ${recall.brand}. 
        Recall: ${recall.hazard}. ${recall.remedy}`}
      accessibilityRole="button"
      accessibilityState={{ expanded }}
      accessibilityActions={[
        { name: 'activate', label: 'View details' },
        { name: 'share', label: 'Share recall' }
      ]}
      onAccessibilityAction={(event) => {
        switch (event.nativeEvent.actionName) {
          case 'activate':
            viewDetails();
            break;
          case 'share':
            shareRecall();
            break;
        }
      }}
      onPress={() => setExpanded(!expanded)}
    >
      {/* Card content */}
    </TouchableOpacity>
  );
}

// Announcements
import { AccessibilityInfo } from 'react-native';

AccessibilityInfo.announceForAccessibility('Recall found for this product');

// Live regions
<Text
  accessibilityLiveRegion="polite"
  accessibilityRole="alert"
>
  {statusMessage}
</Text>
```

---

## 4. Focus Order & Navigation

### iOS Focus Order

```swift
// Set focus order explicitly
override var accessibilityElements: [Any]? {
    get {
        return [
            headerLabel,
            searchTextField,
            searchButton,
            resultsTableView,
            bottomTabBar
        ]
    }
    set {}
}

// Focus management
override func viewDidAppear(_ animated: Bool) {
    super.viewDidAppear(animated)
    
    // Move focus to main content
    UIAccessibility.post(
        notification: .screenChanged,
        argument: headerLabel
    )
}

// Custom focus loop
searchTextField.accessibilityViewIsModal = true

// Skip decorative elements
decorativeImageView.isAccessibilityElement = false

// Focus trapping in modals
modalView.accessibilityViewIsModal = true
```

### Android Focus Order

```xml
<!-- Layout XML -->
<LinearLayout
    android:orientation="vertical">
    
    <TextView
        android:id="@+id/header"
        android:text="@string/header"
        android:importantForAccessibility="yes"
        android:focusable="true"
        android:nextFocusDown="@+id/search_field" />
    
    <EditText
        android:id="@+id/search_field"
        android:hint="@string/search_hint"
        android:nextFocusDown="@+id/search_button"
        android:nextFocusUp="@+id/header" />
    
    <Button
        android:id="@+id/search_button"
        android:text="@string/search"
        android:nextFocusUp="@+id/search_field"
        android:nextFocusDown="@+id/results" />
    
</LinearLayout>
```

```kotlin
// Programmatic focus order
searchField.nextFocusDownId = R.id.search_button
searchButton.nextFocusUpId = R.id.search_field

// Request focus
searchField.requestFocus()

// Skip decorative elements
decorativeImage.importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO

// Focus trapping in dialogs
dialog.setOnShowListener {
    dialogTitleTextView.requestFocus()
}
```

---

## 5. Top 5 Screens Checklist

### Screen 1: Home/Dashboard
- [ ] All interactive elements have labels
- [ ] Focus order: Header → Main action → Content → Navigation
- [ ] Color contrast ≥ 4.5:1 for text
- [ ] Touch targets ≥ 44×44 points
- [ ] Dynamic Type scales properly
- [ ] Screen reader announces page title

### Screen 2: Barcode Scanner
- [ ] Camera permission request is accessible
- [ ] Scanner instructions read by screen reader
- [ ] Scan results announced immediately
- [ ] Alternative text input available
- [ ] Focus returns to appropriate element after scan
- [ ] Flash/torch toggle is labeled

### Screen 3: Search
- [ ] Search field has placeholder and label
- [ ] Keyboard type appropriate (search)
- [ ] Results announced ("X results found")
- [ ] Each result is a single accessible element
- [ ] Filter options are keyboard navigable
- [ ] Loading state announced

### Screen 4: Product/Recall Details
- [ ] All information readable by screen reader
- [ ] Images have alt text
- [ ] Actions clearly labeled
- [ ] Expandable sections announce state
- [ ] Related items are grouped
- [ ] Share action accessible

### Screen 5: Settings
- [ ] All options have labels and values
- [ ] Toggle states announced
- [ ] Grouped by category
- [ ] Changes confirmed with announcement
- [ ] Language selection accessible
- [ ] Sign out confirmation accessible

---

## 6. Testing Tools

### iOS Testing

```swift
// Accessibility Inspector
// Xcode → Open Developer Tool → Accessibility Inspector

// Programmatic testing
import XCTest

class AccessibilityTests: XCTestCase {
    func testButtonAccessibility() {
        let app = XCUIApplication()
        app.launch()
        
        let scanButton = app.buttons["Scan barcode"]
        XCTAssertTrue(scanButton.exists)
        XCTAssertTrue(scanButton.isHittable)
        
        // Check traits
        XCTAssertTrue(scanButton.isAccessibilityElement)
        
        // Check label
        XCTAssertEqual(
            scanButton.label,
            "Scan barcode"
        )
    }
    
    func testContrastRatio() {
        let foreground = UIColor.label
        let background = UIColor.systemBackground
        
        let ratio = foreground.contrastRatio(with: background)
        XCTAssertGreaterThanOrEqual(ratio, 4.5)
    }
}
```

### Android Testing

```kotlin
// Accessibility Scanner
// Download from Play Store

// Espresso tests
@RunWith(AndroidJUnit4::class)
class AccessibilityTest {
    @get:Rule
    val activityRule = ActivityTestRule(MainActivity::class.java)
    
    @Test
    fun testButtonAccessibility() {
        // Check content description
        onView(withId(R.id.scan_button))
            .check(matches(withContentDescription("Scan barcode")))
        
        // Check if clickable
        onView(withId(R.id.scan_button))
            .check(matches(isClickable()))
    }
    
    @Test
    fun testContrastRatio() {
        val foreground = ContextCompat.getColor(context, R.color.text_primary)
        val background = ContextCompat.getColor(context, R.color.background)
        
        val ratio = ContrastChecker.checkContrast(foreground, background)
        assertTrue(ratio >= 4.5)
    }
}

// UI Automator for TalkBack testing
val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())
device.pressHome()
// Enable TalkBack and test navigation
```

---

## 7. Automated Testing Script

```javascript
// axe-core for web views
const axe = require('axe-core');

async function runAccessibilityTests() {
    const results = await axe.run();
    
    console.log('Violations:', results.violations.length);
    results.violations.forEach(violation => {
        console.log(violation.id, violation.description);
        violation.nodes.forEach(node => {
            console.log('  ', node.target);
        });
    });
    
    return results.violations.length === 0;
}

// Pa11y for automated testing
const pa11y = require('pa11y');

async function testAccessibility(url) {
    const results = await pa11y(url, {
        standard: 'WCAG2AA',
        actions: [
            'wait for element #app to be visible',
            'click element #scan-button',
            'wait for element .results to be visible'
        ]
    });
    
    console.log(`Found ${results.issues.length} issues`);
    return results;
}
```

---

## 8. Manual Testing Procedure

### VoiceOver (iOS)
1. **Enable**: Settings → Accessibility → VoiceOver → On
2. **Navigate**: Swipe right/left
3. **Activate**: Double tap
4. **Scroll**: Three-finger swipe
5. **Rotor**: Two-finger rotate

### TalkBack (Android)
1. **Enable**: Settings → Accessibility → TalkBack → On
2. **Navigate**: Swipe right/left
3. **Activate**: Double tap
4. **Scroll**: Two-finger swipe
5. **Reading controls**: Swipe up then right

### Test Cases
1. Navigate entire app with screen reader
2. Complete barcode scan without looking
3. Search for product using voice only
4. Change settings with screen reader
5. Verify all content is announced

---

## 9. Common Issues & Fixes

### Issue: Unlabeled buttons
```swift
// Bad
button.setImage(UIImage(named: "scan"), for: .normal)

// Good
button.setImage(UIImage(named: "scan"), for: .normal)
button.accessibilityLabel = "Scan barcode"
```

### Issue: Poor focus order
```kotlin
// Bad - random focus order

// Good - explicit order
view1.nextFocusDownId = R.id.view2
view2.nextFocusDownId = R.id.view3
view2.nextFocusUpId = R.id.view1
```

### Issue: Missing state announcements
```javascript
// Bad
<TouchableOpacity onPress={() => setExpanded(!expanded)}>

// Good
<TouchableOpacity 
  accessibilityState={{ expanded }}
  onPress={() => setExpanded(!expanded)}>
```

### Issue: Color only information
```swift
// Bad - color only
statusView.backgroundColor = .red // means error

// Good - color plus text/icon
statusView.backgroundColor = .red
statusLabel.text = "Error"
statusIcon.image = UIImage(systemName: "exclamationmark.circle")
```

---

## 10. Resources

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [iOS Accessibility](https://developer.apple.com/accessibility/ios/)
- [Android Accessibility](https://developer.android.com/guide/topics/ui/accessibility)
- [React Native Accessibility](https://reactnative.dev/docs/accessibility)
- [Color Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Accessibility Scanner (Android)](https://play.google.com/store/apps/details?id=com.google.android.apps.accessibility.auditor)
