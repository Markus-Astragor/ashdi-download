from utils import logger

async def user_survey(browser, page):
    try:
            step_index = 0

            while True:
                containers = await page.query_selector_all(".playlists-items")
                if not containers:
                    logger("No .playlists-items found on the page.")
                    return None

                if step_index < 0:
                    logger("Backtracked past first step — aborting.")
                    return None
                if step_index >= len(containers):
                    logger("Ran out of steps without finding ASHDI.")
                    return None

                container = containers[step_index]
                li_handles = await container.query_selector_all("li")

                options: list[tuple] = []
                for li in li_handles:
                    info = await li.evaluate(
                        """el => {
                            const text = (el.innerText || '').trim();
                            const active = el.classList.contains('active');
                            const inlineStyle = el.getAttribute('style') || '';
                            const cs = window.getComputedStyle(el);
                            const visible = !inlineStyle.includes('display: none') && cs.display !== 'none' && cs.visibility !== 'hidden';
                            return { text, active, visible };
                        }"""
                    )
                    if info["visible"] and info["text"]:
                        options.append((li, info))

                if not options:
                    print("There are not any options here")
                    return None

                if step_index == len(containers) - 1:
                    ashdi_idx = None
                    for j, (_, info) in enumerate(options):
                        print('info["text"]', info["text"])
                        if "ashdi" in info["text"].lower():
                            print(f"Found ASHDI player option: {info['text']}")
                            ashdi_idx = j
                            break

                    if ashdi_idx is not None:
                        ashdi_handle, ashdi_info = options[ashdi_idx]
                        print(
                            f"Automatically selecting player: {ashdi_info['text']}")
                        await ashdi_handle.click()
                        await page.wait_for_timeout(500)

                        iframe_element = await page.query_selector("iframe[src*='ashdi.vip']")
                        if iframe_element:
                            src = await iframe_element.get_attribute("src")
                            logger(f"Found iframe with src: {src}")
                            return src

                        print(
                            "ASHDI player selected, but iframe did not appear — going back a step.")
                        step_index = max(step_index - 1, 0)
                        continue
                    else:
                        print(
                            "This player (ASHDI) is not available here — going back a step.")
                        step_index = max(step_index - 1, 0)
                        continue

                if step_index == 0:
                    prompt = "Choose subtitles or voice Enter 1 or 2:"
                elif step_index == 1:
                    prompt = "Choose actor Enter 1 or 2:"
                else:
                    prompt = f"Choose option for step {step_index + 1} Enter number:"

                print(prompt)
                for i, (_, info) in enumerate(options, start=1):
                    active = " (Active)" if info["active"] else ""
                    print(f"{i}. {info['text']}{active}")

                while True:
                    choice_raw = input("Enter number: ").strip()
                    if not choice_raw.isdigit():
                        print("Invalid input — please enter a number.")
                        continue
                    choice_idx = int(choice_raw) - 1
                    if 0 <= choice_idx < len(options):
                        break
                    print("Out of range — please select a valid number.")

                chosen_handle, _ = options[choice_idx]
                await chosen_handle.click()
                await page.wait_for_timeout(500)
                step_index += 1

    finally:
        await browser.close()
        logger("Browser closed (get_player_url).")
        logger("ASHDI iframe not found.")
        return None