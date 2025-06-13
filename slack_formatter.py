#!/usr/bin/env python3

import re


def slack_to_markdown(content: str) -> str:
    """Convert Slack mrkdwn to OpenAI markdown"""
    # Split the input string into parts based on code blocks and inline code
    parts = re.split(r"(?s)(```.+?```|`[^`\n]+?`)", content)

    # Apply the bold, italic, and strikethrough formatting to text not within code
    result = ""
    for part in parts:
        if part.startswith("```") or part.startswith("`"):
            result += part
        else:
            for o, n in [
                (r"\*(?!\s)([^\*\n]+?)(?<!\s)\*", r"**\1**"),  # *bold* to **bold**
                (r"_(?!\s)([^_\n]+?)(?<!\s)_", r"*\1*"),  # _italic_ to *italic*
                (r"~(?!\s)([^~\n]+?)(?<!\s)~", r"~~\1~~"),  # ~strike~ to ~~strike~~
            ]:
                part = re.sub(o, n, part)
            result += part
    return result


def markdown_to_slack(content: str) -> str:
    """Convert OpenAI markdown to Slack mrkdwn"""
    # Split the input string into parts based on code blocks and inline code
    parts = re.split(r"(?s)(```.+?```|`[^`\n]+?`)", content)

    # Apply the bold, italic, and strikethrough formatting to text not within code
    result = ""
    for part in parts:
        if part.startswith("```") or part.startswith("`"):
            result += part
        else:
            for o, n in [
                (
                    r"\*\*\*(?!\s)([^\*\n]+?)(?<!\s)\*\*\*",
                    r"_*\1*_",
                ),  # ***bold italic*** to *_bold italic_*
                (
                    r"(?<![\*_])\*(?!\s)([^\*\n]+?)(?<!\s)\*(?![\*_])",
                    r"_\1_",
                ),  # *italic* to _italic_
                (r"\*\*(?!\s)([^\*\n]+?)(?<!\s)\*\*", r"*\1*"),  # **bold** to *bold*
                (r"__(?!\s)([^_\n]+?)(?<!\s)__", r"*\1*"),  # __bold__ to *bold*
                (r"~~(?!\s)([^~\n]+?)(?<!\s)~~", r"~\1~"),  # ~~strike~~ to ~strike~
            ]:
                part = re.sub(o, n, part)
            result += part
    return result





def format_message_for_slack(content: str) -> str:
    """Complete formatting pipeline for Slack messages"""
    # 1. Convert markdown links [text](url) to Slack format <url|text> FIRST
    content = convert_markdown_links(content)

    # 2. Convert markdown to Slack format
    content = markdown_to_slack(content)

    # 3. Format remaining bare URLs (but skip already formatted ones)
    content = format_remaining_urls(content)

    return content


def convert_markdown_links(content: str) -> str:
    """Convert markdown links [text](url) to Slack format <url|text>"""
    # Pattern to match markdown links: [text](url)
    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

    def replace_markdown_link(match):
        text = match.group(1)
        url = match.group(2)
        return f"<{url}|{text}>"

    return re.sub(markdown_link_pattern, replace_markdown_link, content)


def format_remaining_urls(content: str) -> str:
    """Format remaining bare URLs that aren't already in Slack format"""
    # Pattern to match URLs that are NOT already in Slack format <url|text>
    # This looks for URLs that are not preceded by < and not followed by |
    url_pattern = r'(?<!<)https?://[^\s<>\[\]]+(?:[^\s<>\[\].,;:!?]|[.,;:!?](?!\s|$))*(?!\|)'

    def replace_url(match):
        url = match.group(0)

        # Extract meaningful text from URL
        if 'tecmundo.com.br' in url:
            if 'meta-ai-studio' in url.lower() or ('meta' in url.lower() and 'ai' in url.lower()):
                return f"<{url}|Meta AI Studio chegou ao Brasil>"
            elif 'chatbots' in url.lower():
                return f"<{url}|Artigo sobre Chatbots - TecMundo>"
            else:
                return f"<{url}|Artigo TecMundo>"

        elif 'slack.com' in url:
            return f"<{url}|Ver mensagem no Slack>"

        elif 'youtube.com' in url or 'youtu.be' in url:
            return f"<{url}|Vídeo YouTube>"

        elif 'drive.google.com' in url:
            return f"<{url}|Google Drive>"

        elif 'docs.google.com' in url:
            return f"<{url}|Google Docs>"

        elif 'calendar.google.com' in url:
            return f"<{url}|Google Calendar>"

        elif 'github.com' in url:
            return f"<{url}|GitHub>"

        elif 'linkedin.com' in url:
            return f"<{url}|LinkedIn>"

        else:
            # Extract domain for generic links
            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain:
                domain_name = domain.group(1).replace('www.', '')
                return f"<{url}|{domain_name}>"
            else:
                return f"<{url}|Link>"

    return re.sub(url_pattern, replace_url, content)


# Test function
def test_formatting():
    """Test the formatting functions"""
    # Test with the exact content from user's example
    test_content = """Aqui está um resumo da última mensagem do canal #inovação no Slack:
- **Usuário:** Guilherme Kadow Ferreira (guilherme.kadow)
- **Data/Hora:** 26/03/2025 às 17:24 (horário de Brasília, UTC-3)
- **Conteúdo da mensagem:**
  > https://www.tecmundo.com.br/internet/403590-criador-de-chatbots-meta-ai-studio-chegou-em-portugues-ao-brasil-saiba-como-usar.htm?ab=true&Meta IA estúdio chegou em português no Brasil
- **Link direto para a mensagem:** [Clique aqui para acessar no Slack](https://live-agency.slack.com/archives/C04KKCXMDT9/p1743020684666529)
**Resumo em português:**
Guilherme compartilhou uma notícia do Tecmundo informando que o Meta AI Studio (plataforma de criação de chatbots da Meta) já está disponível em português no Brasil, incluindo instruções de uso para o público local.
Se quiser saber mais detalhes, basta clicar no link do Slack acima."""

    print("ANTES:")
    print(test_content)
    print("\nDEPOIS:")
    print(format_message_for_slack(test_content))

    # Test individual components
    print("\n" + "="*50)
    print("TESTE INDIVIDUAL - BOLD:")
    bold_test = "**Usuário:** Guilherme"
    print(f"Antes: {bold_test}")
    print(f"Depois: {markdown_to_slack(bold_test)}")

    print("\nTESTE INDIVIDUAL - URL:")
    url_test = "https://www.tecmundo.com.br/internet/403590-criador-de-chatbots-meta-ai-studio-chegou-em-portugues-ao-brasil-saiba-como-usar.htm?ab=true"
    print(f"Antes: {url_test}")
    print(f"Depois: {format_remaining_urls(url_test)}")

    print("\nTESTE INDIVIDUAL - MARKDOWN LINK:")
    md_link_test = "[Clique aqui para acessar no Slack](https://live-agency.slack.com/archives/C04KKCXMDT9/p1743020684666529)"
    print(f"Antes: {md_link_test}")
    print(f"Depois: {format_message_for_slack(md_link_test)}")


if __name__ == "__main__":
    test_formatting()
