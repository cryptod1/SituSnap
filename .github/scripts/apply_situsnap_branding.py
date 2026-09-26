from pathlib import Path

def put(path, data):
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(data, encoding="utf-8")

put("app/src/main/res/drawable/situsnap_mark.xml", '''<vector xmlns:android="http://schemas.android.com/apk/res/android"
 android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">
 <path android:fillColor="#071A2B" android:pathData="M0,0h108v108h-108z"/>
 <path android:fillColor="#45F06F" android:pathData="M54,12C34,12 20,27 20,45c0,21 23,39 34,48 11,-9 34,-27 34,-48C88,27 74,12 54,12z"/>
 <path android:fillColor="#081927" android:pathData="M54,25a20,20 0,1 0,0 40a20,20 0,1 0,0 -40"/>
 <path android:fillColor="#F7FAFC" android:pathData="M49,65C43,75 37,85 32,98L43,98C48,84 54,74 63,66z"/>
 <path android:fillColor="#071A2B" android:pathData="M57,68C52,78 49,88 47,98L57,98C60,86 65,77 72,70z"/>
 <path android:fillColor="#39E66C" android:pathData="M67,71C63,81 61,90 61,98L73,98C73,87 76,79 81,72z"/>
</vector>''')

put("app/src/main/res/drawable/situsnap_splash_bg.xml", '''<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
 <gradient android:startColor="#061827" android:endColor="#003C42" android:angle="135"/>
</shape>''')

put("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", '''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
 <background android:drawable="@color/situsnap_icon_bg"/><foreground android:drawable="@drawable/situsnap_mark"/>
</adaptive-icon>''')
put("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", '''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
 <background android:drawable="@color/situsnap_icon_bg"/><foreground android:drawable="@drawable/situsnap_mark"/>
</adaptive-icon>''')
put("app/src/main/res/mipmap-anydpi/ic_launcher.xml", Path("app/src/main/res/drawable/situsnap_mark.xml").read_text(encoding="utf-8"))

put("app/src/main/res/values/colors.xml", '''<resources>
 <color name="situsnap_icon_bg">#071A2B</color><color name="situsnap_green">#39E66C</color>
</resources>''')

put("app/src/main/res/values/styles.xml", '''<resources>
<style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
 <item name="android:fontFamily">sans</item><item name="android:windowLightStatusBar">false</item>
 <item name="android:statusBarColor">#061827</item><item name="android:navigationBarColor">#061827</item>
 <item name="android:windowBackground">@drawable/situsnap_splash_bg</item>
</style>
<style name="SplashTheme" parent="android:style/Theme.Material.Light.NoActionBar">
 <item name="android:fontFamily">sans</item><item name="android:windowLightStatusBar">false</item>
 <item name="android:statusBarColor">#061827</item><item name="android:navigationBarColor">#061827</item>
 <item name="android:windowBackground">@drawable/situsnap_splash_bg</item>
</style></resources>''')

put("app/src/main/java/com/situsnap/app/SplashActivity.java", r'''package com.situsnap.app;
import android.app.Activity; import android.content.Intent; import android.graphics.*;
import android.graphics.drawable.GradientDrawable; import android.os.*; import android.view.*; import android.widget.*;

public class SplashActivity extends Activity {
 static class MarkView extends View {
  Paint p=new Paint(Paint.ANTI_ALIAS_FLAG); MarkView(Activity c){super(c);}
  protected void onDraw(Canvas c){super.onDraw(c); float w=getWidth(),h=getHeight(),s=Math.min(w,h),cx=w/2f,cy=h*.43f;
   Path pin=new Path(); pin.moveTo(cx,cy+s*.38f);
   pin.cubicTo(cx-s*.08f,cy+s*.30f,cx-s*.31f,cy+s*.12f,cx-s*.31f,cy-s*.10f);
   pin.cubicTo(cx-s*.31f,cy-s*.32f,cx-s*.17f,cy-s*.45f,cx,cy-s*.45f);
   pin.cubicTo(cx+s*.17f,cy-s*.45f,cx+s*.31f,cy-s*.32f,cx+s*.31f,cy-s*.10f);
   pin.cubicTo(cx+s*.31f,cy+s*.12f,cx+s*.08f,cy+s*.30f,cx,cy+s*.38f);
   p.setShader(new LinearGradient(cx-s*.25f,cy-s*.35f,cx+s*.25f,cy+s*.25f,Color.rgb(180,255,38),Color.rgb(0,220,103),Shader.TileMode.CLAMP));
   c.drawPath(pin,p); p.setShader(null); p.setColor(Color.rgb(6,24,39)); c.drawCircle(cx,cy-s*.10f,s*.16f,p);
   p.setColor(Color.WHITE); c.drawCircle(cx,cy-s*.10f,s*.075f,p);
   Path road=new Path(); road.moveTo(cx-s*.16f,cy+s*.23f); road.cubicTo(cx-s*.04f,cy+s*.12f,cx+s*.10f,cy+s*.07f,cx+s*.35f,cy+s*.02f);
   road.lineTo(cx+s*.09f,cy+s*.36f); road.lineTo(cx-s*.08f,cy+s*.40f); road.close(); p.setColor(Color.WHITE); c.drawPath(road,p);
   Path stripe=new Path(); stripe.moveTo(cx+s*.02f,cy+s*.27f); stripe.cubicTo(cx+s*.10f,cy+s*.18f,cx+s*.19f,cy+s*.12f,cx+s*.33f,cy+s*.07f);
   stripe.lineTo(cx+s*.15f,cy+s*.37f); stripe.lineTo(cx+s*.07f,cy+s*.39f); stripe.close(); p.setColor(Color.rgb(43,232,100)); c.drawPath(stripe,p);
  }
 }
 TextView tv(String t,int sp,boolean bold){TextView v=new TextView(this);v.setText(t);v.setTextColor(Color.WHITE);v.setTextSize(sp);v.setGravity(Gravity.CENTER);if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return v;}
 public void onCreate(Bundle b){super.onCreate(b); LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setGravity(Gravity.CENTER);
  root.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,new int[]{Color.rgb(6,24,39),Color.rgb(0,52,59)}));root.setPadding(36,36,36,36);
  MarkView mark=new MarkView(this);root.addView(mark,new LinearLayout.LayoutParams(-1,360));root.addView(tv("SituSnap",46,true),new LinearLayout.LayoutParams(-1,-2));
  TextView tag=tv("Find it. Snap it. Update it.",18,false);LinearLayout.LayoutParams tp=new LinearLayout.LayoutParams(-1,-2);tp.topMargin=8;root.addView(tag,tp);
  ProgressBar bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);bar.setIndeterminate(false);bar.setMax(100);bar.setProgress(58);
  LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(260,8);bp.topMargin=70;root.addView(bar,bp);setContentView(root);
  new Handler().postDelayed(()->{startActivity(new Intent(this,MainActivity.class));finish();},850);
 }
}''')

manifest=Path("app/src/main/AndroidManifest.xml")
m=manifest.read_text(encoding="utf-8")
m=m.replace('<application android:theme="@style/AppTheme" android:label="SituSnap" android:usesCleartextTraffic="false">',
'''<application android:theme="@style/AppTheme" android:label="SituSnap" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round" android:usesCleartextTraffic="false">''')
m=m.replace('''<activity android:name=".MainActivity" android:exported="true">
<intent-filter>
<action android:name="android.intent.action.MAIN"/>
<category android:name="android.intent.category.LAUNCHER"/>
</intent-filter>
</activity>''','''<activity android:name=".SplashActivity" android:theme="@style/SplashTheme" android:exported="true">
<intent-filter><action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/></intent-filter>
</activity>
<activity android:name=".MainActivity" android:exported="false"/>''')
manifest.write_text(m,encoding="utf-8")
print("SituSnap branding injected; MainActivity and camera code untouched.")
