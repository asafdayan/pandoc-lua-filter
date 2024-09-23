function BlockQuote(el)
  -- Check if the block quote starts with a callout indicator
  local first_para = el.content[1]
  if first_para and first_para.t == 'Para' then
    local first_inline = first_para.content[1]
    if first_inline and first_inline.t == 'Str' then
      local callout_indicator = first_inline.text:match("^%[!(%w+)%]")
      if callout_indicator then
        -- Remove the callout indicator from the content
        table.remove(first_para.content, 1)
        -- Remove any following space
        if first_para.content[1] and first_para.content[1].t == 'Space' then
          table.remove(first_para.content, 1)
        end

        -- Capture the custom title if present
        local custom_title_inlines = {}
        while first_para.content[1] and first_para.content[1].t ~= 'SoftBreak' do
          table.insert(custom_title_inlines, table.remove(first_para.content, 1))
        end
        -- Remove the SoftBreak if present
        if first_para.content[1] and first_para.content[1].t == 'SoftBreak' then
          table.remove(first_para.content, 1)
        end

        -- Create the LaTeX for the bolded custom title
        local custom_title_latex = ""
        if #custom_title_inlines > 0 then
          -- Combine the inline elements to form the title string
          for _, inline in ipairs(custom_title_inlines) do
            custom_title_latex = custom_title_latex .. pandoc.utils.stringify(inline)
          end
          -- Create the LaTeX for bolding the title and adding a newline after
          custom_title_latex = "\\textbf{" .. custom_title_latex .. "} \\\\"
        end

        -- Map callout types to your tcolorbox environments
        local env_map = {
          NOTE = 'BlueBox',
          WARNING = 'RedBox',
          TIP = 'GreenBox',
          IMPORTANT = 'BlueBox',
          INFO = 'GreenBox',
          -- Add more mappings as needed
        }
        -- Use the appropriate environment or default to 'boxA'
        local env_name = env_map[callout_indicator:upper()] or 'BlueBox'

        -- Prepare the content inside the box
        local blocks = {}  -- Initialize as an empty list

        -- Include the remaining content of the block quote
        for i = 1, #el.content do
          table.insert(blocks, el.content[i])
        end

        -- Manually construct LaTeX code for the content
        local content_blocks = {}

        -- Function to recursively process blocks
        local function process_blocks(blocks)
          for _, block in ipairs(blocks) do
            if block.t == 'Para' then
              -- Process inline elements within the paragraph
              local inline_latex = ""
              for _, inline in ipairs(block.content) do
                if inline.t == 'Math' and inline.mathtype == 'DisplayMath' then
                  inline_latex = inline_latex .. '\n$$' .. inline.text .. '$$\n'
                elseif inline.t == 'Math' and inline.mathtype == 'InlineMath' then
                  inline_latex = inline_latex .. '$' .. inline.text .. '$'
                else
                  inline_latex = inline_latex .. pandoc.utils.stringify(inline)
                end
              end
              table.insert(content_blocks, inline_latex)
            elseif block.t == 'OrderedList' then
              -- Process ordered list
              table.insert(content_blocks, '\\begin{enumerate}\n')
              for _, item in ipairs(block.content) do
                table.insert(content_blocks, '\\item ')
                process_blocks(item)
              end
              table.insert(content_blocks, '\\end{enumerate}\n')
            elseif block.t == 'BulletList' then
              -- Process bullet list
              table.insert(content_blocks, '\\begin{itemize}\n')
              for _, item in ipairs(block.content) do
                table.insert(content_blocks, '\\item ')
                process_blocks(item)
              end
              table.insert(content_blocks, '\\end{itemize}\n')
            elseif block.t == 'Plain' then
              -- Convert inlines to LaTeX
              local inline_latex = pandoc.utils.stringify(block)
              table.insert(content_blocks, inline_latex)
            elseif block.t == 'RawBlock' and block.format == 'latex' then
              -- Include raw LaTeX blocks
              table.insert(content_blocks, block.text .. '\n')
            else
              -- For other block types, use pandoc.write
              local block_latex = pandoc.write(pandoc.Pandoc({block}), 'latex')
              table.insert(content_blocks, block_latex)
            end
          end
        end

        -- Process the blocks
        process_blocks(blocks)

        -- Combine the content
        local inner_latex = table.concat(content_blocks, '\n')

        -- Create the LaTeX code
        local latex_code = '\\begin{' .. env_name .. '}\n' .. custom_title_latex .. '\n' .. inner_latex .. '\n\\end{' .. env_name .. '}'

        -- Return the LaTeX code as a RawBlock
        return pandoc.RawBlock('latex', latex_code)
      end
    end
  end
  -- If not a callout, return the block quote unchanged
  return el
end
