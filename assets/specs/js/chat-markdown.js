/*
 * Renders the assistant's Markdown for the RAG chat.
 *
 * Models often break CommonMark's rules, so `marked` alone leaves raw asterisks or code blocks:
 *   - "**Label:**value" or "**(x)**word" (emphasis next to punctuation),
 *   - the whole answer wrapped in a ```markdown fence,
 *   - lists indented by four spaces (read as code),
 *   - "** spaced **" markers.
 * This file repairs those cases, then sanitises the HTML. Requires marked and DOMPurify.
 *
 * The output is untrusted: a document uploaded to the library could try to steer the model into
 * emitting images (a way to leak the conversation through the URL) or hostile links, so images
 * and other active elements are removed and links open safely in a new tab.
 */
(function () {
    'use strict';

    // Escapes text that is inserted into HTML (user questions, file names, error messages)
    window.escapeHtml = function (value) {
        return String(value === undefined || value === null ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    };

    // If the whole answer is one code fence (markdown, md, text or no language), drop the fence
    function unwrapFence(text) {
        var match = text.trim().match(/^```(?:markdown|md|text)?[ \t]*\n([\s\S]*?)\n?```$/i);
        return match ? match[1] : text;
    }

    // A list indented by four or more spaces (or a tab) is a code block in CommonMark: re-indent it
    function normalizeIndentedLists(text) {
        var inFence = false;
        var previousIsList = false;   // the last non-blank line was a list item
        var runBase = null;           // indentation of the first line of the current indented run
        return text.split('\n').map(function (line) {
            if (/^\s*```/.test(line)) { inFence = !inFence; return line; }
            if (inFence) return line;
            var indented = line.match(/^( {4,}|\t+)((?:[-*+]|\d+[.)])\s+.*)$/);
            if (!indented) {
                if (line.trim() !== '') {
                    previousIsList = /^ {0,3}(?:[-*+]|\d+[.)])\s/.test(line);
                    runBase = null;
                }
                return line;
            }
            var indent = indented[1].replace(/\t/g, '    ').length;
            if (runBase === null) runBase = indent;
            var level = Math.max(0, Math.round((indent - runBase) / 4)) + (previousIsList ? 1 : 0);
            return '    '.repeat(level) + indented[2];
        }).join('\n');
    }

    // Turns the "**text**" that marked left as literal text into <strong> (never inside code)
    function repairBold(root) {
        var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: function (node) {
                if (node.parentElement && node.parentElement.closest('pre, code')) return NodeFilter.FILTER_REJECT;
                return node.nodeValue.indexOf('**') !== -1 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
            }
        });
        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(function (node) {
            var parts = node.nodeValue.split(/\*\*\s*([^*\n]+?)\s*\*\*/g);   // odd positions hold the bold text
            if (parts.length < 3) return;
            var fragment = document.createDocumentFragment();
            parts.forEach(function (part, i) {
                if (i % 2) {
                    var strong = document.createElement('strong');
                    strong.textContent = part;
                    fragment.appendChild(strong);
                } else if (part) {
                    fragment.appendChild(document.createTextNode(part));
                }
            });
            node.parentNode.replaceChild(fragment, node);
        });
    }

    // Links from the model open in a new tab without access to this page
    DOMPurify.addHook('afterSanitizeAttributes', function (node) {
        if (node.tagName === 'A' && node.hasAttribute('href')) {
            node.setAttribute('target', '_blank');
            node.setAttribute('rel', 'noopener noreferrer');
        }
    });

    window.renderMarkdown = function (text) {
        var markdown = normalizeIndentedLists(unwrapFence(String(text === undefined || text === null ? '' : text)));
        var html = DOMPurify.sanitize(marked.parse(markdown, { gfm: true, breaks: true }), {
            FORBID_TAGS: ['img', 'picture', 'source', 'video', 'audio', 'iframe', 'object', 'embed', 'form', 'input',
                          'button', 'select', 'textarea', 'style', 'link', 'meta', 'svg', 'math'],
            FORBID_ATTR: ['style', 'srcset']
        });
        var box = document.createElement('div');
        box.innerHTML = html;
        repairBold(box);
        return box.innerHTML;
    };
})();
