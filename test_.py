import requests

search = input("Search for: ")

url = "https://b9zcrrrvom-dsn.algolia.net/1/indexes/*/queries"
headers = {
    "Content-Type": "application/json",
    "x-algolia-agent": "Algolia for vanilla JavaScript",
    "x-algolia-application-id": "B9ZCRRRVOM",
    "x-algolia-api-key": "1013eebf1ca008149d66ea7a385a1366",
}
payload = {
    "requests": [
        {
            "indexName": "prod_products",
            "params": f"query={search}&hitsPerPage=5&page=0"
        }
    ]
}

res = requests.post(url, json=payload, headers=headers)
res.raise_for_status()
products = res.json()["results"][0]["hits"]

BASE_IMG = "https://www-konga-com-res.cloudinary.com/w_300,f_auto,fl_lossy,dpr_auto,q_auto/media/catalog/product/"
BASE_URL = "https://www.konga.com/product/"
7777
for p in products:
    name = p.get("name")
    pk = p.get("product_id")
    img = BASE_IMG + p.get("image_thumbnail_path", "")
    price = p.get("special_price") or p.get("price")
    old_price = p.get("price") if p.get("special_price") else None
    url = BASE_URL + (p.get("url_key") or str(pk))
    print(f"{name}\n₦{price} (Old: ₦{old_price})\n{url}\n{img}\n{'-'*40}")


