using System;
using System.Windows.Forms;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using Newtonsoft.Json;
using System.Linq;
using System.IO;
using Newtonsoft.Json.Linq;
using System.Drawing;
using Flurl;
using Flurl.Http;
using System.Data.SQLite;
using Dapper;
using System.Security.Cryptography;

namespace Hamster_Key_Generator
{
    public partial class FormMain : Form
    {
        Game[] Games;
        static int progressTime = 0;
        static ToolStripLabel LabelKeys;
        static ToolStripLabel LabelRequest;
        static NumericUpDown DelayNumericInput;
        static ListBox ListBoxKeys;
        static ProgressBar ProgressBarMain;
        static RichTextBox RichTextBoxLogs;


        public FormMain()
        {
            string filePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "games.json");
            string jsonContent = File.ReadAllText(filePath);

            Games = JsonConvert.DeserializeObject<Game[]>(jsonContent);

            using (var connection = new SQLiteConnection("Data Source=keys.db;Version=3;"))
            {
                connection.Open();

                string createTableQuery = @"
                    CREATE TABLE IF NOT EXISTS keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        platform TEXT NOT NULL
                    );";

                connection.Execute(createTableQuery);

                connection.Close();
            }

            InitializeComponent();
        }

        private async void buttonGenerate_Click(object sender, EventArgs e)
        {
            if (comboBoxGames.SelectedIndex<0)
            {
                Log("Please select a game", Color.Orange);
                return;
            }
            Game selectedGame = null;
            // check exists game
            foreach (Game item in Games)
            {
                if (item.name == comboBoxGames.Text)
                {
                    selectedGame = item;
                }
            }

            if (selectedGame == null)
            {
                Log("Selected game not founded!", Color.Orange);
                return;
            }

            buttonGenerate.Enabled = false;
            int countProcess = (int)numericUpDownProccess.Value;
            labelProccess.Text = "Processes: " + countProcess;
            Task[] processes = new Task[countProcess];
            for (int i = 0; i < countProcess; i++)
            {
                if (checkBoxProccessRandomDelay.Checked)
                {
                    await Task.Delay(new Random().Next(0, 5000));
                }
                processes[i] = Process(selectedGame, (int)numericUpDownCount.Value, "Proc_" + (i + 1));
            }

            await Task.WhenAll(processes);
            Log("All processes finished", Color.LimeGreen);
            buttonGenerate.Enabled = true;
        }

        public static async Task<string> Login(string token)
        {
            var url = "https://api.gamepromo.io/promo/login-client";

            var requestHeaders = new HttpRequestMessage(HttpMethod.Post, url);
            // headers
            /*requestHeaders.Headers.Add("Content-Type", "application/json");*/

            // body
            var body = new
            {
                appToken = token,
                clientId = GenerateClientId(),
                clientOrigin = "deviceid"
            };

            var jsonBody = JsonConvert.SerializeObject(body);
            requestHeaders.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");

            HttpClient client = new HttpClient();

            var response = await client.SendAsync(requestHeaders);
            string responseBody = await response.Content.ReadAsStringAsync();
            JObject jsonObject = JObject.Parse(responseBody);
            return jsonObject["clientToken"].ToString();
        }

        public static async Task<int> Request(string clientToken, string promoId)
        {
            var url = "https://api.gamepromo.io/promo/register-event";

            var body = new
            {
                promoId = promoId,
                eventId = Guid.NewGuid().ToString(),
                eventOrigin = "undefined"
            };

            try
            {
                var response = await url
                    .WithOAuthBearerToken(clientToken)
                    .AllowHttpStatus("4xx")
                    .PostJsonAsync(body).ReceiveString();

                var jsonObject = JObject.Parse(response);

                if (jsonObject["hasCode"] != null)
                {
                    return jsonObject.Value<bool>("hasCode") ? 200 : 1;
                }
                else if (jsonObject["error_code"] != null)
                {
                    switch (jsonObject["error_code"].ToString().ToLower())
                    {
                        case "unauthorized":
                            return 2;
                        case "toomanyregister":
                            return 3;
                    }
                }
                return 400;
            }
            catch
            {
                throw;
            }
        }

        public static async Task<string> GenerateKey(string clientToken, string promoId)
        {
            var url = "https://api.gamepromo.io/promo/create-code";

            var body = new
            {
                promoId = promoId
            };

            try
            {
                var response = await url
                        .WithOAuthBearerToken(clientToken)
                        .AllowHttpStatus("4xx")
                        .PostJsonAsync(body).ReceiveString();

                JObject jsonObject = JObject.Parse(response);
                if (jsonObject["promoCode"] != null)
                {
                    return jsonObject["promoCode"].ToString();
                }
                return null;
            }
            catch
            {
                throw;
            }
        }

        public static string GenerateClientId()
        {
            long timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            Random random = new Random();
            string randomNumbers = string.Concat(Enumerable.Range(0, 19).Select(_ => random.Next(10)));
            return $"{timestamp}-{randomNumbers}";
        }

        private void FormMain_Load(object sender, EventArgs e)
        {
            refreshStatics();
            timer1.Start();
            comboBoxGames.Items.Clear();
            for (int i = 0; i < Games.Count(); i++)
            {
                comboBoxGames.Items.Add(Games[i].name);
            }
        }

        static private void Log(string text, Color color = default(Color), string section = null)
        {
            DateTime now = DateTime.Now;
            string formattedTime = now.ToString("HH:mm:ss");
            RichTextBoxLogs.AppendText("[" + formattedTime + "]");
            Color originalColor = RichTextBoxLogs.SelectionColor;
            if (section != null)
            {
                RichTextBoxLogs.AppendText("(");
                RichTextBoxLogs.SelectionColor = GetColorFromText(section);
                RichTextBoxLogs.AppendText(section);
                RichTextBoxLogs.SelectionColor = originalColor;
                RichTextBoxLogs.AppendText(")");
            }
            RichTextBoxLogs.AppendText(" ");
            if (color.IsKnownColor)
            {
                RichTextBoxLogs.SelectionColor = color;
            }
            else
            {
                RichTextBoxLogs.SelectionColor = Color.White;
            }
            RichTextBoxLogs.AppendText(text + "\n");
            RichTextBoxLogs.SelectionColor = originalColor;
            RichTextBoxLogs.ScrollToCaret();
        }

        private void buttonCopy_Click(object sender, EventArgs e)
        {
            if (listBoxKeys.SelectedItem != null)
            {
                Clipboard.SetText(listBoxKeys.SelectedItem.ToString());
                Log("Item copied to clipboard: " + listBoxKeys.SelectedItem.ToString(), Color.Yellow);
            }
            else
            {
                Log("No item selected to copy.", Color.Yellow);
            }
        }

        private void buttonCopyAll_Click(object sender, EventArgs e)
        {
            StringBuilder allItems = new StringBuilder();
            foreach (var item in listBoxKeys.Items)
            {
                allItems.AppendLine(item.ToString());
            }
            Clipboard.SetText(allItems.ToString());
            Log("All items copied to clipboard.", Color.Yellow);
        }

        private void timer1_Tick(object sender, EventArgs e)
        {
            if (progressTime > 0)
            {
                int value = 100 / (progressTime / timer1.Interval);
                if (progressBarMain.Value + value < 100)
                {
                    progressBarMain.Value += value;
                }
            }
        }

        static int AddKeyToDatabase(string key, string platform)
        {
            try
            {
                using (var connection = new SQLiteConnection("Data Source=keys.db;Version=3;"))
                {
                    connection.Open();

                    string checkKeyQuery = "SELECT COUNT(1) FROM keys WHERE key = @Key;";
                    int keyExists = connection.QuerySingle<int>(checkKeyQuery, new { Key = key });

                    if (keyExists > 0)
                    {

                        return 100;
                    }

                    string insertQuery = "INSERT INTO keys (key, platform) VALUES (@Key, @Platform);";
                    var result = connection.Execute(insertQuery, new { Key = key, Platform = platform });

                    return result > 0 ? 200 : 0;
                }
            }
            catch (Exception ex)
            {
                Log("Error: " + ex.Message, Color.Red);
                return 0;
            }
        }

        static private async Task Process(Game g, int keyCount, string processName)
        {
            for (int keyNumber = 1; keyNumber <= keyCount; keyNumber++)
            {
                Log("Start generating key " + keyNumber, section: processName);
                string clientToken = null;
                try
                {
                    clientToken = await Login(g.appToken);
                    Log("Client token: " + clientToken, section: processName);
                }
                catch
                {
                    Log("Login failed", Color.Red, section: processName);
                    await Task.Delay(new Random().Next(0, 3000) + 5000);
                    keyNumber--;
                    continue;
                }

                int attempts = 1;
                int response = 0;
                int surplusDelay = 0;
                bool restartClient = false;
                int repeatedSuccessCount = 0;
                Random rand = new Random();
                Log("Sending requests ...", Color.Cyan, section: processName);
                while (response != 200)
                {
                    int delays = g.eventsDelay + rand.Next(-2000, 2000) + surplusDelay;
                    if (delays < DelayNumericInput.Value)
                    {
                        delays = (int)DelayNumericInput.Value + rand.Next(0, 1000);
                    }
                    if (ProgressBarMain.Value == 0 || ProgressBarMain.Value == 100)
                    {
                        ProgressBarMain.Value = 0;
                        progressTime = delays;
                    }
                    Log("Request " + attempts + " (" + delays.ToString("N0") + ") ...", section: processName);
                    LabelRequest.Text = "Last request: " + attempts;
                    attempts++;
                    await Task.Delay(delays);
                    try
                    {
                        response = await Request(clientToken, g.promoId);
                    }
                    catch
                    {
                        Log("Http error", Color.Red, section: processName);
                        continue;
                    }
                    if (response == 2)
                    {
                        repeatedSuccessCount = 0;
                        Log("Session for client not valid", Color.Red, section: processName);
                        restartClient = true;
                        break;
                    }
                    else if (response == 3)
                    {
                        repeatedSuccessCount = 0;
                        Log("Requests are very fast - Increase delay", Color.Orange, section: processName);
                        surplusDelay += 2000;
                    }
                    else if (response == 400)
                    {
                        repeatedSuccessCount = 0;
                        Log("Undefined error", section: processName);
                    }
                    else if (response == 1)
                    {
                        repeatedSuccessCount++;
                        if (repeatedSuccessCount >= 3)
                        {
                            Log("Delay decreased", Color.Orange, section: processName);
                            surplusDelay -= 1000;
                            repeatedSuccessCount = 0;
                        }
                    }
                    ProgressBarMain.Value = 100;
                }
                if (restartClient)
                {
                    keyNumber--;
                    continue;
                }

                // get key
                string key;
                try
                {
                    key = await GenerateKey(clientToken, g.promoId);
                }
                catch (Exception)
                {
                    Log("Failed to generate key", Color.Red, section: processName);
                    keyNumber--;
                    continue;
                }

                if (string.IsNullOrEmpty(key))
                {
                    Log("Failed to generate key", Color.Red, section: processName);
                    keyNumber--;
                    continue;
                }
                switch (AddKeyToDatabase(key, g.platform))
                {
                    case 0:
                        Log("Failed saving key on database", Color.Red, section: processName);
                        break;
                    case 100:
                        Log("Key exists!", Color.Pink, section: processName);
                        break;
                }
                ListBoxKeys.Items.Add(key);
                ListBoxKeys.TopIndex = ListBoxKeys.Items.Count - 1;
                LabelKeys.Text = "Keys: " + ListBoxKeys.Items.Count;

                Log("Key successfully generated: " + key, Color.LimeGreen, section: processName);
            }
            Log("Process finished", Color.Lime, section: processName);
        }

        private void comboBoxGames_SelectedIndexChanged(object sender, EventArgs e)
        {
            Game selectedGame = null;
            // check exists game
            foreach (Game item in Games)
            {
                if (item.name == comboBoxGames.Text)
                {
                    selectedGame = item;
                }
            }
            if (selectedGame == null)
            {
                return;
            }

            numericUpDownMinimumDelay.Value = selectedGame.eventsDelay;
            refreshStatics();
        }

        private void refreshStatics()
        {
            LabelKeys = labelKeys;
            LabelRequest = labelRequest;
            DelayNumericInput = numericUpDownMinimumDelay;
            ListBoxKeys = listBoxKeys;
            ProgressBarMain = progressBarMain;
            RichTextBoxLogs = richTextBoxLogs;
        }

        public static Color GetColorFromText(string input)
        {
            using (var sha256 = SHA256.Create())
            {
                byte[] hash = sha256.ComputeHash(Encoding.UTF8.GetBytes(input + "artariya"));
                int hue = BitConverter.ToUInt16(hash, 0) % 360;

                return HslToRgb(hue, 1.0, 0.5);
            }
        }

        public static Color HslToRgb(double h, double s, double l)
        {
            double c = (1.0 - Math.Abs(2.0 * l - 1.0)) * s;
            double x = c * (1.0 - Math.Abs((h / 60.0) % 2.0 - 1.0));
            double m = l - c / 2.0;

            double r, g, b;
            if (h < 60)
            {
                r = c; g = x; b = 0;
            }
            else if (h < 120)
            {
                r = x; g = c; b = 0;
            }
            else if (h < 180)
            {
                r = 0; g = c; b = x;
            }
            else if (h < 240)
            {
                r = 0; g = x; b = c;
            }
            else if (h < 300)
            {
                r = x; g = 0; b = c;
            }
            else
            {
                r = c; g = 0; b = x;
            }
            int R = (int)((r + m) * 255);
            int G = (int)((g + m) * 255);
            int B = (int)((b + m) * 255);
            return Color.FromArgb(R, G, B);
        }
    }
}
