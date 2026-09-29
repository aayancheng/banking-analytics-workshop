-- {{< yt ID >}}: a privacy-enhanced YouTube embed on HTML; a titled link in print/EPUB.
-- IDs live in _data/videos.json so a video is registered once and the lint can check it.
local videos = nil

local function load()
  if videos == nil then
    local f = assert(io.open(quarto.project.directory .. "/_data/videos.json", "r"))
    videos = quarto.json.decode(f:read("a"))
    f:close()
  end
  return videos
end

return {
  ["yt"] = function(args)
    local id = pandoc.utils.stringify(args[1])
    local v = load()[id]
    if v == nil then error("yt: unknown video id " .. id) end
    local yid = v.youtube
    if yid == nil or yid == pandoc.null or yid == "" then
      return pandoc.Para({pandoc.Strong(pandoc.Str("Video")), pandoc.Str(": " .. v.title .. " (coming soon)")})
    end
    if quarto.doc.is_format("html") then
      return pandoc.RawBlock("html",
        '<div class="yt"><iframe src="https://www.youtube-nocookie.com/embed/' .. yid ..
        '" title="' .. v.title .. '" loading="lazy" allowfullscreen></iframe></div>')
    end
    return pandoc.Para({pandoc.Strong(pandoc.Str("Video")), pandoc.Str(": "),
                        pandoc.Link(v.title, "https://youtu.be/" .. yid)})
  end
}
