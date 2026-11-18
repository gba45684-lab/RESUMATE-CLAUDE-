# Adds release signing and a always-increasing version code to Capacitor's generated android/app/build.gradle.
import re

p = 'android/app/build.gradle'
s = open(p, encoding='utf-8').read()

signing = (
    '    signingConfigs {\n'
    '        release {\n'
    '            storeFile file("release.keystore")\n'
    '            storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")?.trim()\n'
    '            keyAlias System.getenv("ANDROID_KEY_ALIAS")?.trim()\n'
    '            keyPassword System.getenv("ANDROID_KEY_PASSWORD")?.trim()\n'
    '        }\n'
    '    }\n'
)

assert 'buildTypes {' in s, 'buildTypes block not found'
s = s.replace('    buildTypes {', signing + '    buildTypes {', 1)

s, n = re.subn(r'(buildTypes\s*\{\s*release\s*\{)', r'\1\n            signingConfig signingConfigs.release', s, count=1)
assert n == 1, 'release block not found'

s, n = re.subn(r'versionCode\s+\d+', 'versionCode Integer.parseInt(System.getenv("GITHUB_RUN_NUMBER") ?: "1")', s, count=1)
assert n == 1, 'versionCode not found'

# Release builds: turn on R8 shrinking and obfuscation (Play's code-optimisation and obfuscation checks).
# Capacitor's template ships with minifyEnabled false and the plain proguard-android.txt rules.
s, n = re.subn(r'minifyEnabled\s+false', 'minifyEnabled true\n            shrinkResources true', s, count=1)
assert n == 1, 'minifyEnabled not found in release block'
s, n = re.subn(r"getDefaultProguardFile\('proguard-android\.txt'\)", "getDefaultProguardFile('proguard-android-optimize.txt')", s, count=1)
assert n == 1, 'default proguard file not found'

open(p, 'w', encoding='utf-8').write(s)
print('signing configured')

# Keep the annotations Capacitor reads at runtime to find plugins and their @PluginMethod methods.
# Capacitor's own plugin libraries already ship consumer rules; this only adds attributes R8 must keep.
rules = 'android/app/proguard-rules.pro'
keep = (
    '\n# Keep annotations and debug attributes Capacitor needs at runtime (added by CI).\n'
    '-keepattributes *Annotation*,Signature,SourceFile,LineNumberTable\n'
)
with open(rules, 'a', encoding='utf-8') as f:
    f.write(keep)
print('proguard rules updated')

# Edge-to-edge: the app targets SDK 36, so Android draws behind the system bars anyway.
# Opt in explicitly so the behaviour is intentional; the web UI already pads with env(safe-area-inset-*).
import glob
activities = glob.glob('android/app/src/main/java/**/MainActivity.java', recursive=True)
assert len(activities) == 1, f'expected one MainActivity.java, found {activities}'
activity = activities[0]
pkg = re.search(r'^package\s+([\w.]+);', open(activity, encoding='utf-8').read(), re.M).group(1)
open(activity, 'w', encoding='utf-8').write(
    f'package {pkg};\n\n'
    'import android.os.Bundle;\n'
    'import androidx.activity.EdgeToEdge;\n'
    'import com.getcapacitor.BridgeActivity;\n\n'
    'public class MainActivity extends BridgeActivity {\n'
    '    @Override\n'
    '    public void onCreate(Bundle savedInstanceState) {\n'
    '        super.onCreate(savedInstanceState);\n'
    '        EdgeToEdge.enable(this);\n'
    '    }\n'
    '}\n'
)
print('edge-to-edge enabled in', activity)
