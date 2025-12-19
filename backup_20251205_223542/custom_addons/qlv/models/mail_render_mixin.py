# -*- coding: utf-8 -*-
import re
from lxml import etree, html
from markupsafe import Markup
from odoo import api, models, tools

class MailRenderMixin(models.AbstractModel):
    _inherit = "mail.render.mixin"

    def remove_href_odoo(self, value, remove_parent=True, to_keep=None):
        if not value or len(value) < 20:
            return value
        
        # Ensure value is string
        if isinstance(value, bytes):
            value = value.decode()
            
        has_odoo_link = re.search(r"<a\s(.*)odoo\.com", value, flags=re.IGNORECASE)
        if has_odoo_link:
            if to_keep:
                value = value.replace(to_keep, "<body_msg></body_msg>")
            
            try:
                tree = html.fromstring(value)
                odoo_anchors = tree.xpath('//a[contains(@href,"odoo.com")]')
                for elem in odoo_anchors:
                    parent = elem.getparent()
                    if remove_parent and parent.getparent() is not None:
                        # Remove the parent element (often a 'div' or 'td' wrapping the link)
                        parent.getparent().remove(parent)
                    else:
                        # Just remove the link itself
                        if parent.tag == "td" and parent.getparent():
                             parent.getparent().remove(parent)
                        else:
                             parent.remove(elem)
                             
                value = etree.tostring(
                    tree, pretty_print=True, method="html", encoding="unicode"
                )
            except Exception:
                # If parsing fails, return original value to avoid breaking email
                pass

            if to_keep:
                value = value.replace("<body_msg></body_msg>", to_keep)
                
        return value

    @api.model
    def _render_template(
        self,
        template_src,
        model,
        res_ids,
        engine="inline_template",
        add_context=None,
        options=None,
        post_process=False,
    ):
        original_rendered = super()._render_template(
            template_src,
            model,
            res_ids,
            engine=engine,
            add_context=add_context,
            options=options,
            post_process=post_process,
        )

        for key in res_ids:
            original_rendered[key] = self.remove_href_odoo(original_rendered[key])

        return original_rendered

    def _replace_local_links(self, html, base_url=None):
        message = super()._replace_local_links(html, base_url=base_url)

        wrapper = Markup if isinstance(message, Markup) else str
        message = tools.ustr(message)
        
        # Remove "Powered by Odoo" text/link
        message = re.sub(
            r"""(Powered by\s(.*)Odoo</a>)""", "<div>&nbsp;</div>", message, flags=re.IGNORECASE
        )
        # Remove standalone "Odoo" link if it appears in footer
        message = re.sub(
            r"""<a\s+[^>]*href=['"]https?://www\.odoo\.com['"][^>]*>Odoo</a>""", "", message, flags=re.IGNORECASE
        )

        return wrapper(message)
