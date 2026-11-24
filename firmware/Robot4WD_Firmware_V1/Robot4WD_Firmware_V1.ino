/* Robot Inteligente 4WD - firmware principal 1.0.0 / API 1
 * ESP32 Dev Module. NO instalar en ESP32-CAM.
 * Basado en el cableado de PythonBridge V6. La IA vive en la PC.
 * Configurar credenciales locales antes de cargar. No compartirlas.
 * Salidas a nivel bajo y servos sin PWM al arrancar. Rearme explícito.
 * Los ángulos son órdenes PWM, NO mediciones de posición física.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>
#include <ArduinoOTA.h>
#include <esp_system.h>
#if __has_include(<esp_random.h>)
#include <esp_random.h>
#endif
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <atomic>

// ================= CONFIGURACION LOCAL (editar antes de cargar) ===========
const char* CAMERA_SSID = "ESP32CAM-CARRO";
const char* CAMERA_PASSWORD = "";      // Clave real de la red de la cámara
const char* DIAG_SSID = "Robot4WD_Diagnostico";
const char* DIAG_PASSWORD = "";        // Elegir una clave de 8..63 caracteres
const char* API_KEY = "";              // Elegir una clave distinta de 16..64 caracteres
const bool USE_STATIC_IP = false;     // DHCP por defecto: ver IP en monitor serie
const IPAddress STATIC_IP(192,168,4,200), CAMERA_GATEWAY(192,168,4,1);
const IPAddress MASK(255,255,255,0), DIAG_IP(192,168,10,1);
const bool ENABLE_OTA = false;        // Activar solo con partición OTA y prueba previa
const char* OTA_PASSWORD = "";         // Clave independiente; requerida si ENABLE_OTA
// ========================================================================

const char* FW_VERSION = "1.0.0";
const uint8_t MOTOR_PINS[4][2] = {{26,25},{33,32},{13,12},{14,27}}; // FL FR RL RR
const uint8_t SERVO_PINS[2] = {21,18}; // garra, base
const int SERVO_MIN[2] = {35,35}, SERVO_MAX[2] = {60,115};
const int SERVO_HOME[2] = {60,75};
const uint32_t MIN_PULSE_MS = 50, MAX_PULSE_MS = 700;
const uint32_t LEASE_MS = 1200;        // Heartbeat recomendado: cada 250 ms
const uint32_t SERVO_STEP_MS = 65, SERVO_ENABLE_SETTLE_MS = 800;
const uint32_t SERVO_END_SETTLE_MS = 200;
const int SERVO_STEP_DEG = 2;
const uint32_t MOTOR_DEADTIME_MS = 50; // Tiempo mínimo entre pulsos motrices

WebServer server(80);
Servo servos[2];
SemaphoreHandle_t guard = nullptr;
std::atomic<bool> staUp(false);
std::atomic<uint32_t> networkGeneration(0);
bool otaReady = false;
bool serverReady = false;

// Todo el estado de actuadores se protege con el mismo mutex.
struct RobotState {
  bool armed = false, maintenance = false, motor = false;
  bool attached[2] = {false,false};
  int angle[2] = {60,75}, target[2] = {60,75};
  int direction[4] = {0,0,0,0};
  uint32_t motorStart = 0, motorMs = 0, motorStopped = 0;
  uint32_t lastHeartbeat = 0, lastServoStep = 0;
  uint32_t settleStart[2] = {0,0}, settleMs[2] = {0,0};
  uint32_t challenge = 0, session = 0, lastSeq = 0, netGen = 0;
  const char* reason = "boot";
} st;
struct Command {uint32_t session=0,seq=0;};
uint32_t newToken(uint32_t previous=0);

class Lock {
 public:
  Lock() { xSemaphoreTake(guard, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(guard); }
  Lock(const Lock&) = delete;
  Lock& operator=(const Lock&) = delete;
};
uint32_t elapsed(uint32_t now, uint32_t since) { return now - since; }
uint32_t newToken(uint32_t previous) {
  uint32_t n; do { n = esp_random(); } while (n == 0 || n == previous); return n;
}

// Estas funciones se llaman únicamente bajo mutex, salvo inicialización segura.
void stopWheels(uint32_t now) {
  for(int i=0;i<4;i++) {
    digitalWrite(MOTOR_PINS[i][0],LOW); digitalWrite(MOTOR_PINS[i][1],LOW);
    st.direction[i]=0;
  }
  if(st.motor) st.motorStopped=now;
  st.motor=false; st.motorMs=0;
}
void latchStop(const char* reason, uint32_t now) {
  stopWheels(now);
  for(int i=0;i<2;i++) st.target[i]=st.angle[i]; // Mantener la última orden PWM.
  st.armed=false; st.session=0; st.lastSeq=0;
  st.challenge=newToken(st.challenge); st.reason=reason;
}
bool servoBusy(int i, uint32_t now) {
  return st.attached[i] && (st.angle[i]!=st.target[i] ||
         elapsed(now,st.settleStart[i])<st.settleMs[i]);
}
bool anyServoBusy(uint32_t now) { return servoBusy(0,now)||servoBusy(1,now); }

// Vigilancia independiente del servidor HTTP: una petición lenta no renueva
// el pulso ni el permiso. No realiza operaciones de red dentro del mutex.
void serviceSafety(uint32_t now) {
  if(st.motor && elapsed(now,st.motorStart)>=st.motorMs) stopWheels(now);
  if(st.armed && networkGeneration.load()!=st.netGen) latchStop("network_changed",now);
  if(st.armed && elapsed(now,st.lastHeartbeat)>=LEASE_MS) latchStop("heartbeat_timeout",now);
}
void actuatorTask(void*) {
  TickType_t delayTicks = pdMS_TO_TICKS(5);
  if(delayTicks==0) delayTicks=1;
  for(;;) {
    {
      Lock lock;
      uint32_t now=millis();
      serviceSafety(now);
      if(st.armed && !st.motor && elapsed(now,st.lastServoStep)>=SERVO_STEP_MS) {
        st.lastServoStep=now;
        for(int i=0;i<2;i++) {
          if(!st.attached[i] || st.angle[i]==st.target[i] ||
             elapsed(now,st.settleStart[i])<st.settleMs[i]) continue;
          int delta=st.target[i]-st.angle[i];
          int step=abs(delta)<SERVO_STEP_DEG?abs(delta):SERVO_STEP_DEG;
          st.angle[i] += delta>0?step:-step;
          servos[i].write(st.angle[i]);
          if(st.angle[i]==st.target[i]) {st.settleStart[i]=now; st.settleMs[i]=SERVO_END_SETTLE_MS;}
        }
      }
    }
    vTaskDelay(delayTicks);
  }
}

// ========================== PROTOCOLO HTTP ================================
void sendJson(int code,const String& body) {
  server.sendHeader("Cache-Control","no-store");
  server.send(code,"application/json; charset=utf-8",body);
}
void fail(int code,const char* error) { sendJson(code,String("{\"ok\":false,\"error\":\"")+error+"\"}"); }
bool authorized() {
  if(server.header("X-Robot-Key")==API_KEY) return true;
  fail(403,"unauthorized"); return false;
}
bool readU32(const char* name,uint32_t& out) {
  if(!server.hasArg(name)) return false;
  String s=server.arg(name); if(s.length()==0||s.length()>10) return false;
  uint64_t n=0;
  for(unsigned int i=0;i<s.length();i++) {
    if(s[i]<'0'||s[i]>'9') return false;
    n=n*10+(s[i]-'0'); if(n>0xFFFFFFFFULL) return false;
  }
  out=(uint32_t)n; return true;
}
bool readDirection(const char* name,int& out) {
  String s=server.arg(name);
  if(s=="-1") out=-1; else if(s=="0") out=0; else if(s=="1") out=1; else return false;
  return true;
}
int readServo() {
  String s=server.arg("nombre"); return s=="garra"?0:s=="base"?1:-1;
}
bool readCommand(Command& c) {
  if(readU32("session",c.session)&&readU32("seq",c.seq)&&c.seq!=0) return true;
  fail(400,"session_and_seq_required"); return false;
}
// Debe ejecutarse bajo mutex. Los comandos válidos consumen su secuencia,
// incluso si un interlock los rechaza; nunca reenviar automáticamente movimiento.
const char* acceptCommand(const Command& c,uint32_t now) {
  serviceSafety(now);
  if(!st.armed||st.maintenance) return "not_armed";
  if(c.session!=st.session) return "invalid_session";
  if(c.seq<=st.lastSeq) return "old_sequence";
  st.lastSeq=c.seq; return nullptr;
}
String truth(bool value) {return value?"true":"false";}
void health() {
  sendJson(200,String("{\"ok\":true,\"firmware\":\"Robot4WD\",\"version\":\"")+FW_VERSION+
    "\",\"api_version\":1,\"sta_connected\":"+truth(staUp.load())+"}");
}
void state() {
  if(!authorized()) return;
  RobotState s; uint32_t now;
  {Lock lock; now=millis(); serviceSafety(now); s=st;}
  String j; j.reserve(650);
  j="{\"ok\":true,\"api_version\":1,\"armed\":"; j+=truth(s.armed);
  j+=",\"maintenance\":"; j+=truth(s.maintenance);
  j+=",\"reason\":\"";j+=s.reason;j+="\",\"challenge\":";j+=String(s.challenge);
  j+=",\"last_seq\":";j+=String(s.lastSeq);
  j+=",\"motor_activo\":";j+=truth(s.motor);
  j+=",\"motor_remaining_ms\":";j+=String(s.motor && elapsed(now,s.motorStart)<s.motorMs ? s.motorMs-elapsed(now,s.motorStart):0);
  j+=",\"directions\":[";for(int i=0;i<4;i++){if(i)j+=",";j+=String(s.direction[i]);}j+="]";
  j+=",\"garra\":";j+=String(s.angle[0]);j+=",\"base\":";j+=String(s.angle[1]);
  j+=",\"garra_objetivo\":";j+=String(s.target[0]);j+=",\"base_objetivo\":";j+=String(s.target[1]);
  j+=",\"servo_garra_activo\":";j+=truth(s.attached[0]);j+=",\"servo_base_activo\":";j+=truth(s.attached[1]);
  j+=",\"brazo_ocupado\":";j+=truth((s.attached[0]&&(s.angle[0]!=s.target[0]||elapsed(now,s.settleStart[0])<s.settleMs[0])) || (s.attached[1]&&(s.angle[1]!=s.target[1]||elapsed(now,s.settleStart[1])<s.settleMs[1])));
  j+=",\"heartbeat_remaining_ms\":";j+=String(s.armed&&elapsed(now,s.lastHeartbeat)<LEASE_MS?LEASE_MS-elapsed(now,s.lastHeartbeat):0);
  j+=",\"sta_connected\":";j+=truth(staUp.load());
  j+=",\"sta_ip\":\"";j+=WiFi.localIP().toString();j+="\",\"diag_ip\":\"";j+=WiFi.softAPIP().toString();j+="\"}";
  sendJson(200,j);
}
void arm() {
  if(!authorized()) return;
  uint32_t ch; if(!readU32("challenge",ch)){fail(400,"challenge_required");return;}
  const char* error=nullptr; uint32_t token=0;
  {Lock lock; uint32_t now=millis(); serviceSafety(now);
   if(st.maintenance||st.armed||st.motor) error="cannot_arm";
   else if(ch!=st.challenge) error="invalid_challenge";
   else {st.armed=true; st.session=newToken(st.challenge); token=st.session;
         st.challenge=newToken(st.challenge); st.lastSeq=0; st.lastHeartbeat=now;
         st.netGen=networkGeneration.load(); st.reason="armed";}
  }
  if(error) fail(409,error); else sendJson(200,String("{\"ok\":true,\"session\":")+String(token)+",\"lease_ms\":1200}");
}
void heartbeat() {
  if(!authorized())return; Command c;if(!readCommand(c))return;
  const char* error;
  {Lock lock;uint32_t now=millis();error=acceptCommand(c,now);if(!error)st.lastHeartbeat=now;}
  if(error)fail(409,error);else sendJson(200,"{\"ok\":true}");
}
void stopCommand() {
  // Cualquier cliente de la red local puede detener; nunca puede rearmar sin clave.
  {Lock lock;latchStop("stop_requested",millis());}
  sendJson(200,"{\"ok\":true,\"armed\":false}");
}
void drive() {
  if(!authorized())return; Command c;if(!readCommand(c))return;
  int d[4];uint32_t duration;
  if(!readDirection("fl",d[0])||!readDirection("fr",d[1])||!readDirection("rl",d[2])||!readDirection("rr",d[3])||
     !readU32("ms",duration)||duration<MIN_PULSE_MS||duration>MAX_PULSE_MS||!(d[0]||d[1]||d[2]||d[3])){fail(400,"invalid_drive");return;}
  const char* error;
  {Lock lock;uint32_t now=millis();error=acceptCommand(c,now);
   if(!error && (st.motor||anyServoBusy(now)||elapsed(now,st.motorStopped)<MOTOR_DEADTIME_MS)) error="actuators_busy";
   if(!error) {
     // Los puentes conservan ENA/ENB con jumper: dirección, no velocidad PWM.
     stopWheels(now);
     for(int i=0;i<4;i++) {digitalWrite(MOTOR_PINS[i][0],d[i]>0?HIGH:LOW);digitalWrite(MOTOR_PINS[i][1],d[i]<0?HIGH:LOW);st.direction[i]=d[i];}
     st.motorStart=millis();st.motorMs=duration;st.motor=true;
   }
  }
  if(error)fail(409,error);else sendJson(200,String("{\"ok\":true,\"ms\":")+String(duration)+"}");
}
void enableServo() {
  if(!authorized())return;Command c;if(!readCommand(c))return;int id=readServo();
  if(id<0){fail(400,"invalid_servo");return;}
  const char* error;
  {Lock lock;uint32_t now=millis();error=acceptCommand(c,now);
   if(!error&&!st.attached[id]) {
     if(st.motor||anyServoBusy(now))error="actuators_busy";
     else {
       // La activación puede mover físicamente el eje a HOME. Apoyar el brazo.
       servos[id].setPeriodHertz(50);servos[id].attach(SERVO_PINS[id],500,2400);
       if(!servos[id].attached()){latchStop("servo_attach_failed",millis());error="servo_attach_failed";}
       else {st.attached[id]=true;st.angle[id]=st.target[id]=SERVO_HOME[id];servos[id].write(st.angle[id]);
         st.settleStart[id]=millis();st.settleMs[id]=SERVO_ENABLE_SETTLE_MS;}
     }
   }
  }
  if(error)fail(409,error);else sendJson(200,"{\"ok\":true}");
}
void servoOrder() {
  if(!authorized())return;Command c;if(!readCommand(c))return;int id=readServo();uint32_t degree;
  if(id<0||!readU32("grado",degree)||degree<(uint32_t)SERVO_MIN[id]||degree>(uint32_t)SERVO_MAX[id]){fail(400,"servo_out_of_range");return;}
  const char* error;
  {Lock lock;uint32_t now=millis();error=acceptCommand(c,now);
   if(!error&&!st.attached[id])error="servo_not_enabled";
   if(!error&&(st.motor||anyServoBusy(now)))error="actuators_busy";
   if(!error){st.target[id]=(int)degree;st.lastServoStep=now;}
  }
  if(error)fail(409,error);else sendJson(200,String("{\"ok\":true,\"objetivo\":")+String(degree)+"}");
}
void releaseServo() {
  if(!authorized())return;int id=readServo();
  if(id<0||server.arg("confirm")!="1"){fail(400,"support_arm_and_confirm");return;}
  const char* error=nullptr;
  {Lock lock;uint32_t now=millis();serviceSafety(now);
   if(st.armed||st.motor||st.maintenance)error="stop_before_release";
   else {if(st.attached[id])servos[id].detach();digitalWrite(SERVO_PINS[id],LOW);pinMode(SERVO_PINS[id],OUTPUT);
         st.attached[id]=false;st.target[id]=st.angle[id];st.settleMs[id]=0;}
  }
  if(error)fail(409,error);else sendJson(200,"{\"ok\":true}");
}

// =============================== RED ======================================
bool validSecrets() {
  size_t dp=strlen(DIAG_PASSWORD),ak=strlen(API_KEY),cp=strlen(CAMERA_PASSWORD),op=strlen(OTA_PASSWORD);
  return dp>=8&&dp<=63&&ak>=16&&ak<=64&&cp>=8&&cp<=63&&
         (!ENABLE_OTA||(op>=12&&op<=64&&strcmp(OTA_PASSWORD,API_KEY)!=0))&&strcmp(DIAG_PASSWORD,API_KEY)!=0;
}
void setup() {
  // GPIO12 es pin de strapping: el estado durante reset depende del hardware.
  // La protección por software comienza al ejecutar setup, no antes.
  for(int i=0;i<4;i++)for(int k=0;k<2;k++){digitalWrite(MOTOR_PINS[i][k],LOW);pinMode(MOTOR_PINS[i][k],OUTPUT);digitalWrite(MOTOR_PINS[i][k],LOW);}
  for(int i=0;i<2;i++){digitalWrite(SERVO_PINS[i],LOW);pinMode(SERVO_PINS[i],OUTPUT);digitalWrite(SERVO_PINS[i],LOW);}
  Serial.begin(115200);st.challenge=newToken();st.motorStopped=millis();
  guard=xSemaphoreCreateMutex();
  if(!guard||xTaskCreate(actuatorTask,"actuators",4096,nullptr,3,nullptr)!=pdPASS){Serial.println("ERROR: no se pudo iniciar vigilancia; red deshabilitada.");return;}
  if(!validSecrets()){Serial.println("CONFIGURAR CAMERA_PASSWORD, DIAG_PASSWORD y API_KEY en el sketch. Red deshabilitada por seguridad.");return;}
  WiFi.onEvent([](WiFiEvent_t event){
    if(event==ARDUINO_EVENT_WIFI_STA_GOT_IP){staUp.store(true);networkGeneration.fetch_add(1);}
    else if(event==ARDUINO_EVENT_WIFI_STA_DISCONNECTED||event==ARDUINO_EVENT_WIFI_STA_LOST_IP){if(staUp.exchange(false))networkGeneration.fetch_add(1);}
  });
  WiFi.mode(WIFI_AP_STA);WiFi.setSleep(false);WiFi.setAutoReconnect(true);
  bool ap=WiFi.softAPConfig(DIAG_IP,DIAG_IP,MASK)&&WiFi.softAP(DIAG_SSID,DIAG_PASSWORD);
  Serial.print("Diagnostico AP: ");Serial.println(ap?WiFi.softAPIP().toString():String("ERROR"));
  if(USE_STATIC_IP&&!WiFi.config(STATIC_IP,CAMERA_GATEWAY,MASK))Serial.println("ERROR IP estatica; revisar configuracion.");
  WiFi.begin(CAMERA_SSID,CAMERA_PASSWORD);
  const char* headers[]={"X-Robot-Key"};server.collectHeaders(headers,1);
  server.on("/api/health",HTTP_GET,health);server.on("/api/state",HTTP_GET,state);
  server.on("/api/arm",HTTP_POST,arm);server.on("/api/heartbeat",HTTP_POST,heartbeat);
  server.on("/api/stop",HTTP_POST,stopCommand);server.on("/api/drive",HTTP_POST,drive);
  server.on("/api/servo/enable",HTTP_POST,enableServo);server.on("/api/servo",HTTP_POST,servoOrder);
  server.on("/api/release",HTTP_POST,releaseServo);
  server.on("/",HTTP_GET,[]{sendJson(200,"{\"robot\":\"Robot4WD\",\"api_version\":1,\"health\":\"/api/health\"}");});
  server.onNotFound([](){fail(404,"route_not_found");});server.begin();serverReady=true;
  if(ENABLE_OTA){
    ArduinoOTA.setHostname("robot4wd");ArduinoOTA.setPassword(OTA_PASSWORD);
    ArduinoOTA.onStart([](){Lock lock;latchStop("ota",millis());st.maintenance=true;});
    ArduinoOTA.onError([](ota_error_t){Lock lock;st.maintenance=false;latchStop("ota_error",millis());});
    ArduinoOTA.begin();otaReady=true;
  }
  Serial.println("Robot4WD 1.0.0 / API 1 listo. ARRANQUE DESARMADO.");
  Serial.println("Esperando red de la camara; consultar IP STA en este monitor.");
}
void loop() {
  if(!serverReady){delay(100);return;}
  // Si falló la creación de la tarea, setup no inició servidor ni red.
  static uint32_t printedGen=0;
  uint32_t gen=networkGeneration.load();
  if(gen!=printedGen){printedGen=gen;Serial.print("STA: ");Serial.println(staUp.load()?WiFi.localIP().toString():String("desconectada"));}
  server.handleClient();
  if(otaReady){bool safe;{Lock lock;safe=!st.armed&&!st.motor&&!st.attached[0]&&!st.attached[1];}if(safe)ArduinoOTA.handle();}
  delay(1);
}
