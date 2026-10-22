# Adds release signing and a always-increasing version code to Capacitor's generated android/app/build.gradle.
import re

p = 'android/app/build.gradle'
s = open(p, encoding='utf-8').read()

signing = (
    '    signingConfigs {\n'
    '        release {\n'
    '            storeFile file("release.keystore")\n'
    '            storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")\n'
    '            keyAlias System.getenv("ANDROID_KEY_ALIAS")\n'
    '            keyPassword System.getenv("ANDROID_KEY_PASSWORD")\n'
    '        }\n'
    '    }\n'
)

assert 'buildTypes {' in s, 'buildTypes block not found'
s = s.replace('    buildTypes {', signing + '    buildTypes {', 1)

s, n = re.subn(r'(buildTypes\s*\{\s*release\s*\{)', r'\1\n            signingConfig signingConfigs.release', s, count=1)
assert n == 1, 'release block not found'

s, n = re.subn(r'versionCode\s+\d+', 'versionCode Integer.parseInt(System.getenv("GITHUB_RUN_NUMBER") ?: "1")', s, count=1)
assert n == 1, 'versionCode not found'

open(p, 'w', encoding='utf-8').write(s)
print('signing configured')
