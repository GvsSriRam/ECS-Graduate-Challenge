from parsel import Selector
from playwright.sync_api import sync_playwright
import json, re 
from pathlib import Path

def scrape_researchgate_profile(profile: str):
    with sync_playwright() as p:
        
        profile_data = {
            "basic_info": {},
            "about": {},
            "co_authors": [],
            "publications": [],
        }
        
        browser = p.chromium.launch(headless=True, slow_mo=50)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36")
        page.goto(f"https://www.researchgate.net/profile/{profile}")
        selector = Selector(text=page.content())
        # print(selector)
        profile_data["basic_info"]["name"] = selector.css(".nova-legacy-e-text.nova-legacy-e-text--size-xxl::text").get()
        profile_data["basic_info"]["institution"] = selector.css(".nova-legacy-v-institution-item__stack-item a::text").get()
        profile_data["basic_info"]["department"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__meta-data-item:nth-child(1)").xpath("normalize-space()").get()
        profile_data["basic_info"]["current_position"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__info-section-list-item").xpath("normalize-space()").get()
        profile_data["basic_info"]["lab"] = selector.css(".nova-legacy-o-stack__item .nova-legacy-e-link--theme-bare b::text").get()
        # print(profile_data)
        profile_data["about"]["number_of_publications"] = re.search(r"\d+", selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(1)").xpath("normalize-space()").get()).group()
        profile_data["about"]["reads"] = re.search(r"\d+", selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(2)").xpath("normalize-space()").get()).group()
        profile_data["about"]["citations"] = re.search(r"\d+", selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(3)").xpath("normalize-space()").get()).group()
        profile_data["about"]["introduction"] = selector.css(".nova-legacy-o-stack__item .Linkify").xpath("normalize-space()").get()
        profile_data["about"]["skills"] = selector.css(".nova-legacy-l-flex__item .nova-legacy-e-badge ::text").getall()
        
        for co_author in selector.css(".nova-legacy-c-card--spacing-xl .nova-legacy-c-card__body--spacing-inherit .nova-legacy-v-person-list-item"):
            profile_data["co_authors"].append({
                "name": co_author.css(".nova-legacy-v-person-list-item__align-content .nova-legacy-e-link::text").get(),
                "link": co_author.css(".nova-legacy-l-flex__item a::attr(href)").get(),
                "avatar": co_author.css(".nova-legacy-l-flex__item .lite-page-avatar img::attr(data-src)").get(),
                "current_institution": co_author.css(".nova-legacy-v-person-list-item__align-content li").xpath("normalize-space()").get()
            })

        for publication in selector.css("#publications+ .nova-legacy-c-card--elevation-1-above .nova-legacy-o-stack__item"):
            profile_data["publications"].append({
                "title": publication.css(".nova-legacy-v-publication-item__title .nova-legacy-e-link--theme-bare::text").get(),
                "date_published": publication.css(".nova-legacy-v-publication-item__meta-data-item span::text").get(),
                "authors": publication.css(".nova-legacy-v-person-inline-item__fullname::text").getall(),
                "publication_type": publication.css(".nova-legacy-e-badge--theme-solid::text").get(),
                "description": publication.css(".nova-legacy-v-publication-item__description::text").get(),
                "publication_link": publication.css(".nova-legacy-c-button-group__item .nova-legacy-c-button::attr(href)").get(),
            })
            
            
        # Create output directory if it doesn't exist
        output_path = Path("faculty_scholarly")
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename from profile name
        name = "Venkata S.S. Gandikota"
        filename = f"{name.strip().lower().replace(' ', '_')}.json"
        file_path = output_path / filename
        
        # Save to JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
            
        print(f"Profile data saved to {file_path}")

        browser.close()
        
    return profile_data
        
    
scrape_researchgate_profile(profile="Venkata-Gandikota-2")


# from parsel import Selector
# from playwright.sync_api import sync_playwright
# import json
# import re
# import random
# import time
# def scrape_researchgate_profile(profile: str) -> dict:
#     """
#     Given a profile identifier (e.g. "Carlos-Caicedo-4"),
#     visit the profile page at
#     https://www.researchgate.net/profile/{profile}
#     and return a dictionary containing scraped data.
#     """
#     with sync_playwright() as p:
#         profile_data = {
#             "profile": profile,
#             "basic_info": {},
#             "about": {},
#             "co_authors": [],
#             "publications": [],
#         }
        
#         browser = p.chromium.launch(headless=True, slow_mo=50)
#         page = browser.new_page(
#             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#                        "AppleWebKit/537.36 (KHTML, like Gecko) "
#                        "Chrome/101.0.4951.64 Safari/537.36"
#         )
#         page.goto(f"https://www.researchgate.net/profile/{profile}")
#         # Wait for the network to be idle so that most JS has rendered the page
#         page.wait_for_load_state("networkidle")
#         # Get the page content for parsing
#         selector = Selector(text=page.content())
        
#         # Extract basic info
#         profile_data["basic_info"]["name"] = selector.css(".nova-legacy-l-flex--gutter-xxs>.nova-legacy-l-flex__item::text").get()
#         # profile_data["basic_info"]["institution"] = selector.css(".nova-legacy-v-institution-item__stack-item a::text").get()
#         # profile_data["basic_info"]["department"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__meta-data-item:nth-child(1)").xpath("normalize-space()").get()
#         # profile_data["basic_info"]["current_position"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__info-section-list-item").xpath("normalize-space()").get()
#         # profile_data["basic_info"]["lab"] = selector.css(".nova-legacy-o-stack__item .nova-legacy-e-link--theme-bare b::text").get()
        
#         # Extract 'about' info with regex protection
#         try:
#             profile_data["about"]["number_of_publications"] = re.search(
#                 r"\d+", 
#                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(1)").xpath("normalize-space()").get()
#             ).group()
#         except Exception:
#             profile_data["about"]["number_of_publications"] = None
#         try:
#             profile_data["about"]["reads"] = re.search(
#                 r"\d+", 
#                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(2)").xpath("normalize-space()").get()
#             ).group()
#         except Exception:
#             profile_data["about"]["reads"] = None
#         try:
#             profile_data["about"]["citations"] = re.search(
#                 r"\d+", 
#                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(3)").xpath("normalize-space()").get()
#             ).group()
#         except Exception:
#             profile_data["about"]["citations"] = None

#         profile_data["about"]["introduction"] = selector.css(".nova-legacy-o-stack__item .Linkify").xpath("normalize-space()").get()
#         profile_data["about"]["skills"] = selector.css(".nova-legacy-l-flex__item .nova-legacy-e-badge ::text").getall()
        
#         # Extract co-authors information
#         for co_author in selector.css(".nova-legacy-c-card--spacing-xl .nova-legacy-c-card__body--spacing-inherit .nova-legacy-v-person-list-item"):
#             profile_data["co_authors"].append({
#                 "name": co_author.css(".nova-legacy-v-person-list-item__align-content .nova-legacy-e-link::text").get(),
#                 "link": co_author.css(".nova-legacy-l-flex__item a::attr(href)").get(),
#                 "avatar": co_author.css(".nova-legacy-l-flex__item .lite-page-avatar img::attr(data-src)").get(),
#                 "current_institution": co_author.css(".nova-legacy-v-person-list-item__align-content li").xpath("normalize-space()").get()
#             })

#         # Extract publications information
#         count = 0
#         for publication in selector.css("#publications+ .nova-legacy-c-card--elevation-1-above .nova-legacy-o-stack__item"):
#             if count > 20:
#                 break
#             profile_data["publications"].append({
#                 "title": publication.css(".nova-legacy-v-publication-item__title .nova-legacy-e-link--theme-bare::text").get(),
#                 "date_published": publication.css(".nova-legacy-v-publication-item__meta-data-item span::text").get(),
#                 "authors": publication.css(".nova-legacy-v-person-inline-item__fullname::text").getall(),
#                 "publication_type": publication.css(".nova-legacy-e-badge--theme-solid::text").get(),
#                 "description": publication.css(".nova-legacy-v-publication-item__description::text").get(),
#                 "publication_link": publication.css(".nova-legacy-c-button-group__item .nova-legacy-c-button::attr(href)").get(),
#             })
#             count += 1
        
#         browser.close()
#         return profile_data

# def scrape_profiles(profiles: list, output_file: str):
#     """
#     Given a list of profile identifiers, scrape each profile and
#     write the combined results to the specified JSON file.
#     """
#     all_profiles_data = []
#     for profile in profiles:
#         print(f"Scraping profile: {profile}")
#         try:
#             data = scrape_researchgate_profile(profile)
#             all_profiles_data.append(data)
#         except Exception as e:
#             print(f"Error scraping profile {profile}: {e}")
#         # delay = random.uniform(3, 6)
#         # print(f"Waiting for {delay:.2f} seconds before next profile.")
#         # time.sleep(delay)
    
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(all_profiles_data, f, indent=2, ensure_ascii=False)
#     print(f"Scraped data written to {output_file}")

# # Example list of profile identifiers
# profiles_list = [
#     "Ben-Akih-Kumgeh",
#     # "Mohammad-Abdallah-2",
#     # "Riyad-S-Aboutaha-2026412615"
#     # Add more profile IDs as needed.
# ]

# scrape_profiles(profiles_list, "researchgate_profiles-Ben-Akih-Kumgeh.json")


# # from parsel import Selector
# # from playwright.sync_api import sync_playwright
# # import json
# # import re
# # import time
# # import random

# # def scrape_researchgate_profile(profile: str) -> dict:
# #     """
# #     Scrapes a single ResearchGate profile (e.g. "Carlos-Caicedo-4")
# #     and returns a dictionary with the scraped data.
# #     """
# #     with sync_playwright() as p:
# #         profile_data = {
# #             "profile": profile,
# #             "basic_info": {},
# #             "about": {},
# #             "co_authors": [],
# #             "publications": [],
# #         }
        
# #         browser = p.chromium.launch(headless=True, slow_mo=50)
# #         page = browser.new_page(
# #             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
# #                        "AppleWebKit/537.36 (KHTML, like Gecko) "
# #                        "Chrome/101.0.4951.64 Safari/537.36"
# #         )
# #         # Navigate to the profile page
# #         page.goto(f"https://www.researchgate.net/profile/{profile}")
# #         # Wait for the network to be idle (page load complete)
# #         page.wait_for_load_state("networkidle")
# #         # Add a randomized delay between 2 and 5 seconds
# #         delay = random.uniform(2, 5)
# #         time.sleep(delay)
        
# #         selector = Selector(text=page.content())
# #         # Extract basic info
# #         profile_data["basic_info"]["name"] = selector.css(".nova-legacy-l-flex--gutter-xxs>.nova-legacy-l-flex__item::text").get()
# #         profile_data["basic_info"]["institution"] = selector.css(".nova-legacy-v-institution-item__stack-item a::text").get()
# #         profile_data["basic_info"]["department"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__meta-data-item:nth-child(1)").xpath("normalize-space()").get()
# #         profile_data["basic_info"]["current_position"] = selector.css(".nova-legacy-e-list__item.nova-legacy-v-institution-item__info-section-list-item").xpath("normalize-space()").get()
# #         profile_data["basic_info"]["lab"] = selector.css(".nova-legacy-o-stack__item .nova-legacy-e-link--theme-bare b::text").get()
        
# #         # Extract about information with regex protection
# #         try:
# #             profile_data["about"]["number_of_publications"] = re.search(
# #                 r"\d+", 
# #                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(1)").xpath("normalize-space()").get()
# #             ).group()
# #         except Exception:
# #             profile_data["about"]["number_of_publications"] = None
# #         try:
# #             profile_data["about"]["reads"] = re.search(
# #                 r"\d+", 
# #                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(2)").xpath("normalize-space()").get()
# #             ).group()
# #         except Exception:
# #             profile_data["about"]["reads"] = None
# #         try:
# #             profile_data["about"]["citations"] = re.search(
# #                 r"\d+", 
# #                 selector.css(".nova-legacy-c-card__body .nova-legacy-o-grid__column:nth-child(3)").xpath("normalize-space()").get()
# #             ).group()
# #         except Exception:
# #             profile_data["about"]["citations"] = None

# #         profile_data["about"]["introduction"] = selector.css(".nova-legacy-o-stack__item .Linkify").xpath("normalize-space()").get()
# #         profile_data["about"]["skills"] = selector.css(".nova-legacy-l-flex__item .nova-legacy-e-badge ::text").getall()
        
# #         # Extract co-authors
# #         for co_author in selector.css(".nova-legacy-c-card--spacing-xl .nova-legacy-c-card__body--spacing-inherit .nova-legacy-v-person-list-item"):
# #             profile_data["co_authors"].append({
# #                 "name": co_author.css(".nova-legacy-v-person-list-item__align-content .nova-legacy-e-link::text").get(),
# #                 "link": co_author.css(".nova-legacy-l-flex__item a::attr(href)").get(),
# #                 "avatar": co_author.css(".nova-legacy-l-flex__item .lite-page-avatar img::attr(data-src)").get(),
# #                 "current_institution": co_author.css(".nova-legacy-v-person-list-item__align-content li").xpath("normalize-space()").get()
# #             })

# #         # Extract publications
# #         for publication in selector.css("#publications+ .nova-legacy-c-card--elevation-1-above .nova-legacy-o-stack__item"):
# #             profile_data["publications"].append({
# #                 "title": publication.css(".nova-legacy-v-publication-item__title .nova-legacy-e-link--theme-bare::text").get(),
# #                 "date_published": publication.css(".nova-legacy-v-publication-item__meta-data-item span::text").get(),
# #                 "authors": publication.css(".nova-legacy-v-person-inline-item__fullname::text").getall(),
# #                 "publication_type": publication.css(".nova-legacy-e-badge--theme-solid::text").get(),
# #                 "description": publication.css(".nova-legacy-v-publication-item__description::text").get(),
# #                 "publication_link": publication.css(".nova-legacy-c-button-group__item .nova-legacy-c-button::attr(href)").get(),
# #             })
            
# #         browser.close()
# #         return profile_data

# # def scrape_profiles(profiles: list, output_file: str):
# #     """
# #     Given a list of profile identifiers, scrape each profile,
# #     and write the combined results to the specified JSON file.
# #     """
# #     all_profiles_data = []
# #     for profile in profiles:
# #         print(f"Scraping profile: {profile}")
# #         try:
# #             data = scrape_researchgate_profile(profile)
# #             all_profiles_data.append(data)
# #         except Exception as e:
# #             print(f"Error scraping profile {profile}: {e}")
# #         # Add a random delay between profiles (e.g., 3 to 6 seconds)
# #         delay = random.uniform(3, 6)
# #         print(f"Waiting for {delay:.2f} seconds before next profile.")
# #         time.sleep(delay)
    
# #     with open(output_file, 'w', encoding='utf-8') as f:
# #         json.dump(all_profiles_data, f, indent=2, ensure_ascii=False)
# #     print(f"Scraped data written to {output_file}")

# # # Example list of profile identifiers (update with your full list)
# # profiles_list = [
# #     "Carlos-Caicedo-4",
# #     "Mohammad-Abdallah-2",
# #     # "Riyad-S-Aboutaha-2026412615"
# #     # Add more profile IDs as needed.
# # ]

# # scrape_profiles(profiles_list, "researchgate_profiles.json")
