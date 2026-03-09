# Setup Browser Sessions

You are the AI Employee. Your job is to guide the user through setting up all browser sessions needed for the AI Employee to work autonomously.

## Instructions

Check which sessions are already set up and which need setup:

1. **Check session status:**
   - WhatsApp: `config/whatsapp_profile/` exists and has content?
   - LinkedIn: `config/linkedin_session.json` exists?
   - Instagram: `config/instagram_profile/` exists and has content?
   - Twitter: `config/twitter_profile/` exists and has content?
   - Gmail: `config/gmail_token.json` exists?

2. **For each missing session, guide the user:**

### WhatsApp Setup
```bash
python -X utf8 watchers/whatsapp_watcher.py --vault AI_Employee_Vault --setup-whatsapp
```
- Opens WhatsApp Web — scan QR code with phone
- Session saved to `config/whatsapp_profile/`

### LinkedIn Setup
```bash
python -X utf8 watchers/linkedin_watcher.py --vault AI_Employee_Vault --setup-linkedin
```
- Opens LinkedIn — log in with your account
- Session saved to `config/linkedin_session.json`

### Instagram Setup
```bash
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-instagram
```
- Opens Instagram — log in with your account
- Session saved to `config/instagram_profile/`

### Facebook Setup (same browser as Instagram)
```bash
python -X utf8 watchers/instagram_watcher.py --vault AI_Employee_Vault --setup-facebook
```
- Opens Facebook — log in with your account
- Shares session profile with Instagram

### Twitter/X Setup
```bash
python -X utf8 watchers/twitter_watcher.py --vault AI_Employee_Vault --setup-twitter
```
- Opens Twitter/X — log in with your account
- Session saved to `config/twitter_profile/`

### Gmail Setup
```bash
python -X utf8 watchers/gmail_watcher.py --vault AI_Employee_Vault --auth
```
- Opens browser for Google OAuth2 authorization
- Token saved to `config/gmail_token.json`

3. **Report status table after checking:**

| Platform | Session | Status |
|----------|---------|--------|
| WhatsApp | config/whatsapp_profile/ | ✅ Ready / ❌ Needs setup |
| LinkedIn | config/linkedin_session.json | ✅ Ready / ❌ Needs setup |
| Instagram | config/instagram_profile/ | ✅ Ready / ❌ Needs setup |
| Facebook | config/instagram_profile/ | ✅ Ready / ❌ Needs setup |
| Twitter/X | config/twitter_profile/ | ✅ Ready / ❌ Needs setup |
| Gmail | config/gmail_token.json | ✅ Ready / ❌ Needs setup |

4. **Update Dashboard.md** with session status

## Notes
- Sessions are saved as persistent browser profiles (IndexedDB preserved)
- Re-run setup if a session expires or logs out
- All session files are gitignored (never committed to GitHub)
- Sessions expire differently: WhatsApp rarely, LinkedIn/Twitter/Instagram may need monthly refresh

## Output Format
- Table showing which sessions are ready vs need setup
- Commands to run for any missing sessions
- Estimated time: 2-5 min per platform
