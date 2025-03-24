import os
import re
import git
import json
import time
import hashlib
import logging
import requests
import schedule
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer

# Configuration
DOMAINS_FILE = "portfolio.txt"
OUTPUT_DIR = "portfolio"
THUMBNAILS_DIR = os.path.join(OUTPUT_DIR, "thumbnails")
DATA_FILE = os.path.join(OUTPUT_DIR, "data.json")
GIT_REPO_PATH = OUTPUT_DIR
GIT_REMOTE = "origin"
GIT_BRANCH = "main"
HTTP_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("portfolio_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("portfolio_generator")


def normalize_url(url):
    """Normalize URL to standard format."""
    url = url.strip().lower()

    # Add http:// if no protocol specified
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    # Parse URL and reconstruct it
    parsed = urlparse(url)
    hostname = parsed.netloc

    # Remove www. if present
    if hostname.startswith('www.'):
        hostname = hostname[4:]

    # Return normalized URL
    return f"{parsed.scheme}://{hostname}"


def get_domain_content(url):
    """Fetch website content."""
    try:
        headers = {
            'User-Agent': USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def analyze_content(html_content):
    """Analyze website content to identify theme and technologies."""
    if not html_content:
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract text for theme/keywords analysis
    text_content = soup.get_text(separator=' ', strip=True)

    # Very simple NLP with TF-IDF to extract keywords
    try:
        # Simple preprocessing
        text_content = re.sub(r'\s+', ' ', text_content).lower()

        # Extract keywords with TF-IDF
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words='english',
            ngram_range=(1, 2)
        )

        # Ensure we have enough text to analyze
        if len(text_content.split()) < 10:
            keywords = []
        else:
            tfidf_matrix = vectorizer.fit_transform([text_content])
            feature_names = vectorizer.get_feature_names_out()

            # Get top keywords
            scores = zip(feature_names, tfidf_matrix.toarray()[0])
            sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
            keywords = [word for word, score in sorted_scores[:10] if score > 0]

        # Cluster text to identify theme
        if len(text_content.split()) < 20:
            theme = "Unknown"
        else:
            # Simple theme identification based on keyword frequency
            common_themes = {
                "ecommerce": ["shop", "cart", "product", "buy", "price", "store", "shipping"],
                "blog": ["blog", "post", "article", "author", "comment", "read"],
                "portfolio": ["portfolio", "work", "project", "gallery", "showcase"],
                "corporate": ["company", "business", "service", "solution", "client", "partner"],
                "news": ["news", "article", "latest", "update", "publish", "press"],
                "education": ["course", "learn", "student", "education", "training", "class"],
                "technology": ["tech", "software", "app", "digital", "innovation", "solution"]
            }

            # Count theme-related words
            theme_scores = {}
            for theme_name, theme_words in common_themes.items():
                score = sum(1 for word in theme_words if word in text_content)
                theme_scores[theme_name] = score

            # Get the theme with the highest score
            max_score = max(theme_scores.values()) if theme_scores else 0
            if max_score > 0:
                theme = max(theme_scores.items(), key=lambda x: x[1])[0]
            else:
                theme = "General"

        # Detect technologies
        tech_patterns = {
            "WordPress": ["wp-content", "wp-includes", "wordpress"],
            "React": ["react", "reactjs", "jsx"],
            "Angular": ["angular", "ng-"],
            "Vue.js": ["vue", "vuejs"],
            "Bootstrap": ["bootstrap"],
            "jQuery": ["jquery"],
            "PHP": ["php"],
            "Laravel": ["laravel"],
            "Django": ["django"],
            "Flask": ["flask"],
            "Node.js": ["node", "nodejs"],
            "Express": ["express"],
            "MongoDB": ["mongodb", "mongo"],
            "MySQL": ["mysql"],
            "PostgreSQL": ["postgresql", "postgres"],
            "Ruby on Rails": ["rails", "ruby on rails"],
            "Shopify": ["shopify"],
            "Wix": ["wix"],
            "Squarespace": ["squarespace"],
            "Webflow": ["webflow"],
            "Gatsby": ["gatsby"],
            "Next.js": ["next.js", "nextjs"],
            "Nuxt.js": ["nuxt.js", "nuxtjs"],
            "Svelte": ["svelte"],
            "TypeScript": ["typescript"],
            "Tailwind CSS": ["tailwind"],
            "Material UI": ["material-ui", "mui"],
            "GraphQL": ["graphql"],
            "Redux": ["redux"],
            "Firebase": ["firebase"],
            "AWS": ["aws", "amazon web services"],
            "Google Cloud": ["gcp", "google cloud"],
            "Azure": ["azure", "microsoft azure"],
            "Cloudflare": ["cloudflare"],
            "Netlify": ["netlify"],
            "Vercel": ["vercel"],
            "Heroku": ["heroku"],
            "Docker": ["docker"],
            "Kubernetes": ["kubernetes", "k8s"],
            "Webpack": ["webpack"],
            "Babel": ["babel"],
            "ESLint": ["eslint"],
            "Jest": ["jest"],
            "Mocha": ["mocha"],
            "Cypress": ["cypress"],
            "Google Analytics": ["google analytics", "ga"],
            "Stripe": ["stripe"],
            "PayPal": ["paypal"],
            "Algolia": ["algolia"],
            "Contentful": ["contentful"],
            "Sanity": ["sanity.io", "sanity"],
            "Drupal": ["drupal"],
            "Joomla": ["joomla"],
            "Magento": ["magento"],
            "WooCommerce": ["woocommerce"],
            "PrestaShop": ["prestashop"],
            "OpenCart": ["opencart"],
            "Elementor": ["elementor"],
            "Divi": ["divi"],
            "Gutenberg": ["gutenberg"],
            "SASS/SCSS": ["sass", "scss"],
            "Less": ["less"],
            "Styled Components": ["styled-components", "styled components"],
            "Emotion": ["emotion"],
            "Chakra UI": ["chakra"],
            "Ant Design": ["antd", "ant design"],
            "Semantic UI": ["semantic-ui", "semantic ui"],
            "Bulma": ["bulma"],
            "Foundation": ["foundation"],
            "Alpine.js": ["alpine.js", "alpinejs"],
            "Stimulus": ["stimulus"],
            "Ember": ["ember"],
            "Backbone.js": ["backbone"],
            "Meteor": ["meteor"],
            "Socket.io": ["socket.io", "socketio"],
            "D3.js": ["d3.js", "d3"],
            "Three.js": ["three.js", "threejs"],
            "Chart.js": ["chart.js", "chartjs"],
            "Highcharts": ["highcharts"],
            "Plotly": ["plotly"],
            "Leaflet": ["leaflet"],
            "Mapbox": ["mapbox"],
            "Auth0": ["auth0"],
            "Okta": ["okta"],
            "Sentry": ["sentry"],
            "New Relic": ["newrelic", "new relic"],
            "Datadog": ["datadog"],
            "Amplitude": ["amplitude"],
            "Mixpanel": ["mixpanel"],
            "Hotjar": ["hotjar"],
            "Intercom": ["intercom"],
            "Zendesk": ["zendesk"],
            "Hubspot": ["hubspot"],
            "Mailchimp": ["mailchimp"],
            "SendGrid": ["sendgrid"],
            "Twilio": ["twilio"],
            "Cloudinary": ["cloudinary"],
            "Akamai": ["akamai"],
            "Fastly": ["fastly"],
            "Vimeo": ["vimeo"],
            "YouTube": ["youtube"],
            "Disqus": ["disqus"],
            "Discourse": ["discourse"],
            "Ghost": ["ghost"],
            "Medium": ["medium"],
            "Webmentions": ["webmention"],
            "IndieWeb": ["indieweb"],
            "Microformats": ["microformats", "h-card", "h-entry"],
            "JSON-LD": ["json-ld", "jsonld"],
            "Schema.org": ["schema.org", "schema"],
            "Open Graph": ["og:"],
            "Twitter Cards": ["twitter:"],
            "AMP": ["amp-", "accelerated mobile pages"],
            "PWA": ["progressive web app", "service-worker.js", "manifest.json"],
            "WebAssembly": ["wasm", "webassembly"],
            "WebGL": ["webgl"],
            "WebRTC": ["webrtc"],
            "WebSockets": ["websocket"],
            "Web Components": ["custom-elements", "shadow-dom", "web components"],
            "Lit": ["lit-element", "lit-html", "lit"],
            "Stencil": ["stencil"],
            "Polymer": ["polymer"],
            "Ionic": ["ionic"],
            "Capacitor": ["capacitor"],
            "Cordova": ["cordova"],
            "Flutter": ["flutter"],
            "React Native": ["react-native", "react native"],
            "Swift": ["swift"],
            "Kotlin": ["kotlin"],
            "Unity": ["unity"],
            "Unreal Engine": ["unreal"],
            "Godot": ["godot"],
            "Electron": ["electron"],
            "Tauri": ["tauri"],
            "NW.js": ["nw.js", "nwjs"],
            "Deno": ["deno"],
            "Bun": ["bun"],
            "Vite": ["vite"],
            "Parcel": ["parcel"],
            "Rollup": ["rollup"],
            "esbuild": ["esbuild"],
            "SWC": ["swc"],
            "Rome": ["rome"],
            "Prettier": ["prettier"],
            "Husky": ["husky"],
            "Storybook": ["storybook"],
            "Nx": ["nx"],
            "Turborepo": ["turborepo"],
            "Lerna": ["lerna"],
            "pnpm": ["pnpm"],
            "Yarn": ["yarn"],
            "npm": ["npm"],
            "Astro": ["astro"],
            "Remix": ["remix"],
            "SolidJS": ["solid-js", "solidjs"],
            "Preact": ["preact"],
            "Qwik": ["qwik"],
            "htmx": ["htmx"],
            "Alpine.js": ["alpine.js", "alpinejs"],
            "Hotwire": ["hotwire", "turbo", "stimulus"],
            "LiveView": ["liveview"],
            "Livewire": ["livewire"],
            "Inertia.js": ["inertia", "inertiajs"],
            "tRPC": ["trpc"],
            "Prisma": ["prisma"],
            "Sequelize": ["sequelize"],
            "TypeORM": ["typeorm"],
            "Mongoose": ["mongoose"],
            "Drizzle": ["drizzle-orm", "drizzle"],
            "Supabase": ["supabase"],
            "Hasura": ["hasura"],
            "Directus": ["directus"],
            "Strapi": ["strapi"],
            "KeystoneJS": ["keystone"],
            "Payload CMS": ["payload cms", "payload"],
            "Craft CMS": ["craft cms", "craft"],
            "Statamic": ["statamic"],
            "Kirby": ["kirby"],
            "Wagtail": ["wagtail"],
            "Umbraco": ["umbraco"],
            "Kentico": ["kentico"],
            "Sitecore": ["sitecore"],
            "Adobe Experience Manager": ["aem", "adobe experience manager"],
            "Contentstack": ["contentstack"],
            "Storyblok": ["storyblok"],
            "DatoCMS": ["datocms", "dato cms"],
            "Prismic": ["prismic"],
            "Builder.io": ["builder.io"],
            "Webflow CMS": ["webflow cms"],
            "Plasmic": ["plasmic"],
            "Framer": ["framer"],
            "Figma": ["figma"],
            "Sketch": ["sketch"],
            "Adobe XD": ["adobe xd", "xd"],
            "InVision": ["invision"],
            "Zeplin": ["zeplin"],
            "Abstract": ["abstract"],
            "Miro": ["miro"],
            "Notion": ["notion"],
            "Airtable": ["airtable"],
            "Coda": ["coda"],
            "Monday": ["monday"],
            "Asana": ["asana"],
            "Trello": ["trello"],
            "Jira": ["jira"],
            "Linear": ["linear"],
            "ClickUp": ["clickup"],
            "Basecamp": ["basecamp"],
            "Slack": ["slack"],
            "Discord": ["discord"],
            "Microsoft Teams": ["teams", "microsoft teams"],
            "Google Workspace": ["google workspace"],
            "Microsoft 365": ["microsoft 365", "office 365"],
            "Zoom": ["zoom"],
            "Google Meet": ["google meet", "meet"],
            "Microsoft Teams": ["teams", "microsoft teams"],
            "WebEx": ["webex"],
            "GoToMeeting": ["gotomeeting"],
            "BlueJeans": ["bluejeans"],
            "Whereby": ["whereby"],
            "Calendly": ["calendly"],
            "Google Calendar": ["google calendar"],
            "Microsoft Outlook": ["outlook"],
            "Salesforce": ["salesforce"],
            "HubSpot": ["hubspot"],
            "Marketo": ["marketo"],
            "Mailchimp": ["mailchimp"],
            "Klaviyo": ["klaviyo"],
            "Brevo": ["brevo", "sendinblue"],
            "ActiveCampaign": ["activecampaign"],
            "ConvertKit": ["convertkit"],
            "Constant Contact": ["constant contact"],
            "Campaign Monitor": ["campaign monitor"],
            "GetResponse": ["getresponse"],
            "AWeber": ["aweber"],
            "Drip": ["drip"],
            "Omnisend": ["omnisend"],
            "Iterable": ["iterable"],
            "Customer.io": ["customer.io"],
            "Segment": ["segment"],
            "Google Tag Manager": ["gtm", "google tag manager"],
            "Tealium": ["tealium"],
            "Ensighten": ["ensighten"],
            "Adobe Analytics": ["adobe analytics"],
            "Matomo": ["matomo", "piwik"],
            "Plausible": ["plausible"],
            "Fathom": ["fathom"],
            "Simple Analytics": ["simple analytics"],
            "Heap": ["heap"],
            "FullStory": ["fullstory"],
            "LogRocket": ["logrocket"],
            "Mouseflow": ["mouseflow"],
            "Crazy Egg": ["crazy egg", "crazyegg"],
            "Optimizely": ["optimizely"],
            "VWO": ["vwo", "visual website optimizer"],
            "AB Tasty": ["ab tasty", "abtasty"],
            "Convert": ["convert.com"],
            "Unbounce": ["unbounce"],
            "Instapage": ["instapage"],
            "Leadpages": ["leadpages"],
            "Landingi": ["landingi"],
            "Webflow": ["webflow"],
            "Bubble": ["bubble.io", "bubble"],
            "Glide": ["glide"],
            "Adalo": ["adalo"],
            "Softr": ["softr"],
            "Carrd": ["carrd"],
            "Tilda": ["tilda"],
            "Readymag": ["readymag"],
            "Framer": ["framer"],
            "Squarespace": ["squarespace"],
            "Wix": ["wix"],
            "Shopify": ["shopify"],
            "BigCommerce": ["bigcommerce"],
            "WooCommerce": ["woocommerce"],
            "Magento": ["magento"],
            "PrestaShop": ["prestashop"],
            "OpenCart": ["opencart"],
            "Salesforce Commerce Cloud": ["salesforce commerce", "demandware"],
            "Adobe Commerce": ["adobe commerce"],
            "Swell": ["swell.is", "swell"],
            "Medusa": ["medusajs", "medusa"],
            "CommerceJS": ["commerce.js", "commercejs"],
            "Snipcart": ["snipcart"],
            "Stripe": ["stripe"],
            "PayPal": ["paypal"],
            "Square": ["square"],
            "Adyen": ["adyen"],
            "Braintree": ["braintree"],
            "Klarna": ["klarna"],
            "Affirm": ["affirm"],
            "Afterpay": ["afterpay"],
            "Clearpay": ["clearpay"],
            "Zip": ["zip"],
            "Sezzle": ["sezzle"],
            "Amazon Pay": ["amazon pay"],
            "Google Pay": ["google pay"],
            "Apple Pay": ["apple pay"],
            "Shop Pay": ["shop pay"],
            "Bolt": ["bolt"],
            "Fast": ["fast"],
            "Algolia": ["algolia"],
            "Elasticsearch": ["elasticsearch"],
            "Meilisearch": ["meilisearch"],
            "Typesense": ["typesense"],
            "Solr": ["solr"],
            "Coveo": ["coveo"],
            "Constructor.io": ["constructor.io"],
            "Klevu": ["klevu"],
            "Searchspring": ["searchspring"],
            "Nosto": ["nosto"],
            "Dynamic Yield": ["dynamic yield"],
            "Bloomreach": ["bloomreach"],
            "Sitecore": ["sitecore"],
            "Contentful": ["contentful"],
            "Sanity": ["sanity"],
            "Strapi": ["strapi"],
            "Contentstack": ["contentstack"],
            "Storyblok": ["storyblok"],
            "Prismic": ["prismic"],
            "DatoCMS": ["datocms"],
            "Kontent.ai": ["kontent.ai", "kentico kontent"],
            "Agility CMS": ["agility cms"],
            "Builder.io": ["builder.io"],
            "Plasmic": ["plasmic"],
            "Webiny": ["webiny"],
            "Ghost": ["ghost"],
            "WordPress": ["wordpress"],
            "Drupal": ["drupal"],
            "Joomla": ["joomla"],
            "TYPO3": ["typo3"],
            "Umbraco": ["umbraco"],
            "Sitefinity": ["sitefinity"],
            "Kentico": ["kentico"],
            "Episerver": ["episerver", "optimizely cms"],
            "Adobe Experience Manager": ["aem", "adobe experience manager"],
            "Sitecore": ["sitecore"],
            "Acquia": ["acquia"],
            "Pantheon": ["pantheon"],
            "WP Engine": ["wp engine", "wpengine"],
            "Kinsta": ["kinsta"],
            "Flywheel": ["flywheel"],
            "Cloudways": ["cloudways"],
            "Digital Ocean": ["digitalocean", "digital ocean"],
            "Linode": ["linode"],
            "Vultr": ["vultr"],
            "AWS": ["aws", "amazon web services", "ec2", "s3"],
            "Google Cloud": ["gcp", "google cloud"],
            "Azure": ["azure", "microsoft azure"],
            "Heroku": ["heroku"],
            "Netlify": ["netlify"],
            "Vercel": ["vercel"],
            "Cloudflare": ["cloudflare"],
            "Fastly": ["fastly"],
            "Akamai": ["akamai"],
            "Imperva": ["imperva"],
            "Sucuri": ["sucuri"],
            "Wordfence": ["wordfence"],
            "Cloudflare Workers": ["cloudflare workers"],
            "AWS Lambda": ["lambda"],
            "Azure Functions": ["azure functions"],
            "Google Cloud Functions": ["cloud functions"],
            "Firebase": ["firebase"],
            "Supabase": ["supabase"],
            "Nhost": ["nhost"],
            "Appwrite": ["appwrite"],
            "Back4App": ["back4app"],
            "Parse": ["parse"],
            "Realm": ["realm"],
            "Amplify": ["amplify"],
            "Hasura": ["hasura"],
            "Neon": ["neon.tech", "neon"],
            "PlanetScale": ["planetscale"],
            "Xata": ["xata"],
            "Turso": ["turso"],
            "Upstash": ["upstash"],
            "Fauna": ["fauna"],
            "Convex": ["convex"],
            "Deno Deploy": ["deno deploy"],
            "Cloudflare Pages": ["cloudflare pages"],
            "Cloudflare Workers": ["cloudflare workers"],
            "Fly.io": ["fly.io"],
            "Railway": ["railway"],
            "Render": ["render"],
            "Koyeb": ["koyeb"],
            "Qovery": ["qovery"],
            "Northflank": ["northflank"],
            "Porter": ["porter"],
            "Coolify": ["coolify"],
            "Dokku": ["dokku"],
            "Caprover": ["caprover"],
            "Kubernetes": ["kubernetes", "k8s"],
            "Docker": ["docker"],
            "Podman": ["podman"],
            "Nomad": ["nomad"],
            "Terraform": ["terraform"],
            "Pulumi": ["pulumi"],
            "Ansible": ["ansible"],
            "Chef": ["chef"],
            "Puppet": ["puppet"],
            "Salt": ["salt", "saltstack"],
            "GitHub Actions": ["github actions"],
            "GitLab CI": ["gitlab ci"],
            "CircleCI": ["circleci"],
            "Travis CI": ["travis ci"],
            "Jenkins": ["jenkins"],
            "TeamCity": ["teamcity"],
            "Bamboo": ["bamboo"],
            "Bitbucket Pipelines": ["bitbucket pipelines"],
            "Azure DevOps": ["azure devops"],
            "AWS CodePipeline": ["codepipeline"],
            "Google Cloud Build": ["cloud build"],
            "Drone": ["drone.io", "drone"],
            "Concourse": ["concourse"],
            "Argo CD": ["argo cd", "argocd"],
            "Flux": ["flux"],
            "Spinnaker": ["spinnaker"],
            "Harness": ["harness"],
            "Octopus Deploy": ["octopus deploy"],
            "Buildkite": ["buildkite"],
            "Semaphore": ["semaphore"],
            "Codefresh": ["codefresh"],
            "Buddy": ["buddy"],
            "Appveyor": ["appveyor"],
            "CodeShip": ["codeship"],
            "Wercker": ["wercker"],
            "Shippable": ["shippable"],
            "Nevercode": ["nevercode"],
            "Codemagic": ["codemagic"],
            "Bitrise": ["bitrise"],
            "App Center": ["app center"],
            "Firebase App Distribution": ["firebase app distribution"],
            "TestFlight": ["testflight"],
            "Play Console": ["play console"],
            "Expo": ["expo"],
            "Sentry": ["sentry"],
            "Bugsnag": ["bugsnag"],
            "Rollbar": ["rollbar"],
            "LogRocket": ["logrocket"],
            "Datadog": ["datadog"],
            "New Relic": ["new relic", "newrelic"],
            "Dynatrace": ["dynatrace"],
            "AppDynamics": ["appdynamics"],
            "Elastic APM": ["elastic apm"],
            "Prometheus": ["prometheus"],
            "Grafana": ["grafana"],
            "Kibana": ["kibana"],
            "Loki": ["loki"],
            "Jaeger": ["jaeger"],
            "Zipkin": ["zipkin"],
            "OpenTelemetry": ["opentelemetry"],
            "Instana": ["instana"],
            "Lightstep": ["lightstep"],
            "Honeycomb": ["honeycomb"],
            "Splunk": ["splunk"],
            "Sumo Logic": ["sumo logic"],
            "Logz.io": ["logz.io"],
            "Loggly": ["loggly"],
            "Papertrail": ["papertrail"],
            "Graylog": ["graylog"],
            "Fluentd": ["fluentd"],
            "Logstash": ["logstash"],
            "Vector": ["vector"],
            "OpenSearch": ["opensearch"],
            "Algolia": ["algolia"],
            "Meilisearch": ["meilisearch"],
            "Typesense": ["typesense"],
            "Elasticsearch": ["elasticsearch"],
            "Solr": ["solr"],
            "Vespa": ["vespa"],
            "Weaviate": ["weaviate"],
            "Pinecone": ["pinecone"],
            "Qdrant": ["qdrant"],
            "Milvus": ["milvus"],
            "Chroma": ["chroma"],
            "LanceDB": ["lancedb"],
            "OpenAI": ["openai"],
            "Anthropic": ["anthropic", "claude"],
            "Cohere": ["cohere"],
            "Hugging Face": ["huggingface", "hugging face"],
            "Replicate": ["replicate"],
            "Stability AI": ["stability.ai", "stability ai"],
            "Midjourney": ["midjourney"],
            "Runway": ["runway"],
            "LangChain": ["langchain"],
            "LlamaIndex": ["llamaindex"],
            "Vercel AI SDK": ["vercel ai sdk"],
            "Fixie": ["fixie"],
            "Perplexity": ["perplexity"],
            "Groq": ["groq"],
            "Together AI": ["together.ai", "together ai"],
            "Mistral AI": ["mistral.ai", "mistral ai"],
            "Ollama": ["ollama"],
            "LocalAI": ["localai", "local ai"],
            "LM Studio": ["lm studio"],
            "Jan": ["jan.ai", "jan"],
            "Bedrock": ["bedrock"],
            "Vertex AI": ["vertex ai"],
            "Azure OpenAI": ["azure openai"],
            "Gemini": ["gemini"],
            "GPT": ["gpt"],
            "DALL-E": ["dall-e", "dalle"],
            "Stable Diffusion": ["stable diffusion"],
            "Midjourney": ["midjourney"],
            "Firefly": ["firefly"],
            "Imagen": ["imagen"],
            "Claude": ["claude"],
            "Llama": ["llama"],
            "Mixtral": ["mixtral"],
            "Falcon": ["falcon"],
            "Whisper": ["whisper"],
            "TensorFlow": ["tensorflow"],
            "PyTorch": ["pytorch"],
            "JAX": ["jax"],
            "Keras": ["keras"],
            "scikit-learn": ["scikit-learn", "sklearn"],
            "XGBoost": ["xgboost"],
            "LightGBM": ["lightgbm"],
            "CatBoost": ["catboost"],
            "Pandas": ["pandas"],
            "NumPy": ["numpy"],
            "SciPy": ["scipy"],
            "Matplotlib": ["matplotlib"],
            "Seaborn": ["seaborn"],
            "Plotly": ["plotly"],
            "D3.js": ["d3.js", "d3"],
            "Three.js": ["three.js", "threejs"],
            "Babylon.js": ["babylon.js", "babylonjs"],
            "PlayCanvas": ["playcanvas"],
            "Pixi.js": ["pixi.js", "pixijs"],
            "p5.js": ["p5.js", "p5js"],
            "Paper.js": ["paper.js", "paperjs"],
            "Fabric.js": ["fabric.js", "fabricjs"],
            "Chart.js": ["chart.js", "chartjs"],
            "Highcharts": ["highcharts"],
            "ApexCharts": ["apexcharts"],
            "ECharts": ["echarts"],
            "Recharts": ["recharts"],
            "Victory": ["victory"],
            "Nivo": ["nivo"],
            "Visx": ["visx"],
            "Vega": ["vega"],
            "Vega-Lite": ["vega-lite"],
            "Observable": ["observable"],
            "Leaflet": ["leaflet"],
            "Mapbox": ["mapbox"],
            "OpenLayers": ["openlayers"],
            "Google Maps": ["google maps", "googlemaps"],
            "Maplibre": ["maplibre"],
            "Cesium": ["cesium"],
            "Deck.gl": ["deck.gl", "deckgl"],
            "Kepler.gl": ["kepler.gl", "keplergl"],
            "ArcGIS": ["arcgis"],
            "QGIS": ["qgis"],
            "Turf.js": ["turf.js", "turfjs"],
            "Proj4js": ["proj4js"],
            "Nominatim": ["nominatim"],
            "OpenStreetMap": ["openstreetmap"],
            "HERE": ["here maps", "here"],
            "TomTom": ["tomtom"],
            "Bing Maps": ["bing maps"],
            "Mapbox GL": ["mapbox gl"],
            "Tangram": ["tangram"],
            "Maptiler": ["maptiler"],
            "Stadia Maps": ["stadia maps"],
            "Thunderforest": ["thunderforest"],
            "Carto": ["carto"],
            "Mapzen": ["mapzen"],
            "Jawg": ["jawg"],
            "Geoapify": ["geoapify"],
            "Foursquare": ["foursquare"],
            "Factual": ["factual"],
            "Radar": ["radar.io", "radar"],
            "Esri": ["esri"],
            "Mapillary": ["mapillary"],
            "Strava": ["strava"],
            "Garmin": ["garmin"],
            "Komoot": ["komoot"],
            "Peloton": ["peloton"],
            "Zwift": ["zwift"],
            "Fitbit": ["fitbit"],
            "Apple Health": ["apple health"],
            "Google Fit": ["google fit"],
            "Samsung Health": ["samsung health"],
            "Withings": ["withings"],
            "Oura": ["oura"],
            "Whoop": ["whoop"],
            "Strava": ["strava"],
            "Garmin": ["garmin"],
            "Polar": ["polar"],
            "Suunto": ["suunto"],
            "Coros": ["coros"],
            "MyFitnessPal": ["myfitnesspal"],
            "Cronometer": ["cronometer"],
            "Lifesum": ["lifesum"],
            "Noom": ["noom"],
            "Weight Watchers": ["weight watchers", "ww"],
            "Headspace": ["headspace"],
            "Calm": ["calm"],
            "Waking Up": ["waking up"],
            "Insight Timer": ["insight timer"],
            "Peloton": ["peloton"],
            "Zwift": ["zwift"],
            "TrainerRoad": ["trainerroad"],
            "Sufferfest": ["sufferfest"],
            "Strava": ["strava"],
            "Komoot": ["komoot"],
            "AllTrails": ["alltrails"],
            "Wikiloc": ["wikiloc"],
            "Gaia GPS": ["gaia gps"],
            "Trailforks": ["trailforks"],
            "Relive": ["relive"],
            "Ride with GPS": ["ride with gps"],
            "Wahoo": ["wahoo"],
            "Hammerhead": ["hammerhead"],
            "Karoo": ["karoo"],
            "Garmin": ["garmin"],
            "Suunto": ["suunto"],
            "Polar": ["polar"],
            "Coros": ["coros"],
            "Fitbit": ["fitbit"],
            "Apple Watch": ["apple watch"],
            "Samsung Galaxy Watch": ["galaxy watch"],
            "Withings": ["withings"],
            "Oura": ["oura"],
            "Whoop": ["whoop"],
            "Biostrap": ["biostrap"],
            "Levels": ["levels"],
            "Dexcom": ["dexcom"],
            "Freestyle Libre": ["freestyle libre"],
            "Medtronic": ["medtronic"],
            "Omron": ["omron"],
            "Withings": ["withings"],
            "iHealth": ["ihealth"],
            "Qardio": ["qardio"],
            "Omada": ["omada"],
            "Livongo": ["livongo"],
            "Virta": ["virta"],
            "Noom": ["noom"],
            "Weight Watchers": ["weight watchers", "ww"],
            "Headspace": ["headspace"],
            "Calm": ["calm"],
            "Waking Up": ["waking up"],
            "Insight Timer": ["insight timer"],
            "Talkspace": ["talkspace"],
            "BetterHelp": ["betterhelp"],
            "Cerebral": ["cerebral"],
            "Lyra": ["lyra"],
            "Ginger": ["ginger"],
            "Spring Health": ["spring health"],
            "Modern Health": ["modern health"],
            "Teladoc": ["teladoc"],
            "Amwell": ["amwell"],
            "Doctor on Demand": ["doctor on demand"],
            "MDLIVE": ["mdlive"],
            "Zocdoc": ["zocdoc"],
            "One Medical": ["one medical"],
            "Forward": ["forward"],
            "Carbon Health": ["carbon health"],
            "Parsley Health": ["parsley health"],
            "Tia": ["tia"],
            "Kindbody": ["kindbody"],
            "Maven": ["maven"],
            "Ro": ["ro"],
            "Hims": ["hims"],
            "Hers": ["hers"],
            "Nurx": ["nurx"],
            "Pill Club": ["pill club"],
            "Simple Health": ["simple health"],
            "Lemonaid": ["lemonaid"],
            "GoodRx": ["goodrx"],
            "Blink Health": ["blink health"],
            "Capsule": ["capsule"],
            "Alto": ["alto"],
            "PillPack": ["pillpack"],
            "Truepill": ["truepill"],
            "NowRx": ["nowrx"],
            "ScriptDash": ["scriptdash"],
            "Medly": ["medly"],
            "Instacart": ["instacart"],
            "DoorDash": ["doordash"],
            "Uber Eats": ["uber eats"],
            "Grubhub": ["grubhub"],
            "Postmates": ["postmates"],
            "Caviar": ["caviar"],
            "Seamless": ["seamless"],
            "Deliveroo": ["deliveroo"],
            "Just Eat": ["just eat"],
            "Delivery Hero": ["delivery hero"],
            "Glovo": ["glovo"],
            "Rappi": ["rappi"],
            "iFood": ["ifood"],
            "Swiggy": ["swiggy"],
            "Zomato": ["zomato"],
            "Uber": ["uber"],
            "Lyft": ["lyft"],
            "Bolt": ["bolt"],
            "Grab": ["grab"],
            "Gojek": ["gojek"],
            "Didi": ["didi"],
            "Ola": ["ola"],
            "Careem": ["careem"],
            "BlaBlaCar": ["blablacar"],
            "Via": ["via"],
            "Citymapper": ["citymapper"],
            "Transit": ["transit"],
            "Moovit": ["moovit"],
            "Lime": ["lime"],
            "Bird": ["bird"],
            "Spin": ["spin"],
            "Tier": ["tier"],
            "Voi": ["voi"],
            "Dott": ["dott"],
            "Superpedestrian": ["superpedestrian"],
            "Neuron": ["neuron"],
            "Beam": ["beam"],
            "Nextbike": ["nextbike"],
            "Mobike": ["mobike"],
            "Jump": ["jump"],
            "Citi Bike": ["citi bike"],
            "Divvy": ["divvy"],
            "Capital Bikeshare": ["capital bikeshare"],
            "Bluebikes": ["bluebikes"],
            "Bay Wheels": ["bay wheels"],
            "Biki": ["biki"],
            "Bixi": ["bixi"],
            "Vélib": ["velib"],
            "Santander Cycles": ["santander cycles"],
            "Call a Bike": ["call a bike"],
            "Donkey Republic": ["donkey republic"],
            "Lime": ["lime"],
            "Bird": ["bird"],
            "Spin": ["spin"],
            "Tier": ["tier"],
            "Voi": ["voi"],
            "Dott": ["dott"],
            "Superpedestrian": ["superpedestrian"],
            "Neuron": ["neuron"],
            "Beam": ["beam"],
            "Nextbike": ["nextbike"],
            "Mobike": ["mobike"],
            "Jump": ["jump"],
            "Citi Bike": ["citi bike"],
            "Divvy": ["divvy"],
            "Capital Bikeshare": ["capital bikeshare"],
            "Bluebikes": ["bluebikes"],
            "Bay Wheels": ["bay wheels"],
            "Biki": ["biki"],
            "Bixi": ["bixi"],
            "Vélib": ["velib"],
            "Santander Cycles": ["santander cycles"],
            "Call a Bike": ["call a bike"],
            "Donkey Republic": ["donkey republic"]
        }

        # Detect technologies
        technologies = []
        html_str = str(soup).lower()

        for tech, patterns in tech_patterns.items():
            for pattern in patterns:
                if pattern.lower() in html_str:
                    technologies.append(tech)
                    break

        # Remove duplicates
        technologies = list(set(technologies))

        return {
            "theme": theme,
            "keywords": keywords,
            "technologies": technologies
        }
    except Exception as e:
        logger.error(f"Error analyzing content: {e}")
        return {
            "theme": "Unknown",
            "keywords": [],
            "technologies": []
        }

def capture_thumbnail(url, domain_name):
    """Capture a thumbnail of the website."""
    try:
        # Since we can't use Selenium or similar tools with the resource constraints,
        # we'll try to find and use the largest image on the page as a thumbnail
        headers = {
            'User-Agent': USER_AGENT
        }
        response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Try to find the largest image
        largest_image = None
        max_size = 0

        # Check for open graph image first
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image.get('content')
            if not img_url.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                img_url = f"{base_url.scheme}://{base_url.netloc}{img_url}"

            try:
                img_response = requests.get(img_url, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))

                # Save thumbnail
                os.makedirs(THUMBNAILS_DIR, exist_ok=True)
                thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
                img = img.convert('RGB')  # Convert to RGB for JPG
                img.thumbnail((300, 200))  # Resize to thumbnail
                img.save(thumbnail_path, 'JPEG')
                return thumbnail_path
            except Exception as e:
                logger.warning(f"Could not use og:image for {url}: {e}")

        # If og:image fails, try to find the largest image
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue

            # Convert relative URLs to absolute
            if not src.startswith(('http://', 'https://')):
                base_url = urlparse(url)
                src = f"{base_url.scheme}://{base_url.netloc}{src}"

            try:
                img_response = requests.get(src, headers=headers, timeout=HTTP_TIMEOUT)
                img_response.raise_for_status()
                img = Image.open(BytesIO(img_response.content))

                # Calculate image size
                size = img.width * img.height

                # Update largest image if this one is bigger
                if size > max_size:
                    max_size = size
                    largest_image = img
            except Exception:
                continue

        # Save the largest image as thumbnail
        if largest_image:
            os.makedirs(THUMBNAILS_DIR, exist_ok=True)
            thumbnail_path = os.path.join(THUMBNAILS_DIR, f"{domain_name}.jpg")
            largest_image = largest_image.convert('RGB')  # Convert to RGB for JPG
            largest_image.thumbnail((300, 200))  # Resize to thumbnail
            largest_image.save(thumbnail_path, 'JPEG')
            return thumbnail_path

        # If no suitable image found, create a placeholder
        return None
    except Exception as e:
        logger.error(f"Error capturing thumbnail for {url}: {e}")
        return None

def get_color_for_domain(domain):
    """Generate a consistent color hex code for a domain."""
    hash_value = 0
    for char in domain:
        hash_value = ((hash_value << 5) - hash_value) + ord(char)
        hash_value = hash_value & 0xFFFFFF

    # Convert to hex and ensure it's 6 characters
    hex_color = format(hash_value & 0xFFFFFF, '06x')
    return hex_color

def get_initials(domain):
    """Get initials from domain name."""
    domain_name = domain.split('.')[0]
    if len(domain_name) >= 2:
        return domain_name[:2].upper()
    return domain_name.upper()

def generate_description(site):
    """Generate a brief description from the site data."""
    keywords = site.get("keywords", [])
    if not keywords:
        return f"This appears to be a {site.get('theme', 'general').lower()} website."

    keyword_text = ", ".join(keywords[:3])
    return f"This {site.get('theme', 'website').lower()} focuses on {keyword_text}."

def init_git_repo():
    """Initialize or update git repository."""
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Check if it's already a git repo
        try:
            repo = git.Repo(GIT_REPO_PATH)
            logger.info("Git repository already initialized")
        except git.exc.InvalidGitRepositoryError:
            # Initialize new repo
            repo = git.Repo.init(GIT_REPO_PATH)
            logger.info("Initialized new git repository")

            # Add .gitignore
            with open(os.path.join(GIT_REPO_PATH, ".gitignore"), "w") as f:
                f.write(
                    "__pycache__/\n*.py[cod]\n*$py.class\n.env\n.venv\nenv/\nvenv/\nENV/\nenv.bak/\nvenv.bak/\n")

            # Initial commit
            repo.git.add(".")
            repo.git.commit("-m", "Initial commit")

        return repo
    except Exception as e:
        logger.error(f"Error initializing git repository: {e}")
        return None

def commit_and_push_changes(repo):
    """Commit and push changes to git repository."""
    if not repo:
        return

    try:
        # Check if there are changes
        if not repo.is_dirty() and not repo.untracked_files:
            logger.info("No changes to commit")
            return

        # Add all changes
        repo.git.add(".")

        # Commit changes
        commit_message = f"Update portfolio data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        repo.git.commit("-m", commit_message)
        logger.info(f"Committed changes: {commit_message}")

        # Push to remote if configured
        try:
            origin = repo.remote(name=GIT_REMOTE)
            origin.push(GIT_BRANCH)
            logger.info(f"Pushed changes to {GIT_REMOTE}/{GIT_BRANCH}")
        except Exception as e:
            logger.warning(f"Could not push to remote: {e}")
    except Exception as e:
        logger.error(f"Error committing changes: {e}")

def find_most_common_theme(portfolio_data):
    """Find the most common theme in the portfolio data."""
    themes = {}
    for site in portfolio_data:
        theme = site.get("theme", "Unknown")
        themes[theme] = themes.get(theme, 0) + 1

    if not themes:
        return "None"

    # Return the theme with the highest count
    return max(themes.items(), key=lambda x: x[1])[0]

def main():
    """Main function to generate the portfolio."""
    try:
        # Create output directories
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(THUMBNAILS_DIR, exist_ok=True)

        # Initialize git repository
        repo = init_git_repo()

        # Load existing data if available
        existing_data = []
        existing_domains = {}

        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

                # Create a lookup dictionary for faster access
                for site in existing_data:
                    existing_domains[site.get("domain", "")] = site

                logger.info(f"Loaded {len(existing_data)} existing sites from {DATA_FILE}")
            except Exception as e:
                logger.error(f"Error loading existing data: {e}")

        # Load domains from file
        try:
            with open(DOMAINS_FILE, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(domains)} domains from {DOMAINS_FILE}")
        except Exception as e:
            logger.error(f"Error loading domains: {e}")
            domains = []

        # Process each domain
        new_domains = 0
        updated_domains = 0

        for domain in domains:
            try:
                # Normalize URL
                url = normalize_url(domain)
                domain_name = urlparse(url).netloc

                # Create a hash of the domain name for filenames
                domain_hash = hashlib.md5(domain_name.encode()).hexdigest()

                logger.info(f"Processing {domain_name}")

                # Check if we already have data for this domain
                if domain_name in existing_domains:
                    # Skip if processed recently (less than 7 days ago)
                    last_updated = existing_domains[domain_name].get("last_updated", "")
                    if last_updated:
                        try:
                            last_date = datetime.strptime(last_updated, "%Y-%m-%d")
                            days_since_update = (datetime.now() - last_date).days
                            if days_since_update < 7:
                                logger.info(f"Skipping {domain_name} - updated {days_since_update} days ago")
                                continue
                        except Exception:
                            # If date parsing fails, process anyway
                            pass

                # Fetch website content
                html_content = get_domain_content(url)
                if not html_content:
                    logger.warning(f"Could not fetch content for {domain_name}")
                    continue

                # Analyze content
                analysis = analyze_content(html_content)

                # Capture thumbnail
                thumbnail_path = capture_thumbnail(url, domain_name)

                # Create or update site data
                site_data = {
                    "domain": domain_name,
                    "url": url,
                    "theme": analysis["theme"],
                    "keywords": analysis["keywords"],
                    "technologies": analysis["technologies"],
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "description": ""
                }

                # Generate description
                site_data["description"] = generate_description(site_data)

                # Update existing data or add new entry
                if domain_name in existing_domains:
                    # Update existing entry
                    for i, site in enumerate(existing_data):
                        if site.get("domain") == domain_name:
                            existing_data[i] = site_data
                            break
                    updated_domains += 1
                    logger.info(f"Updated data for {domain_name}")
                else:
                    # Add new entry
                    existing_data.append(site_data)
                    new_domains += 1
                    logger.info(f"Added new data for {domain_name}")

                # Sleep to avoid rate limiting
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error processing {domain}: {e}")

        # Save updated data
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2)

        logger.info(f"Saved data for {len(existing_data)} sites to {DATA_FILE}")
        logger.info(f"Added {new_domains} new domains, updated {updated_domains} existing domains")

        # Commit and push changes
        commit_and_push_changes(repo)

        return True
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        return False

if __name__ == "__main__":
    # Run once
    success = main()

    if success:
        logger.info("Portfolio generation completed successfully")
    else:
        logger.error("Portfolio generation failed")


