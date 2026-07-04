# frozen_string_literal: true

class SourceosDevtools < Formula
  desc "SourceOS developer and Portable AI Kit operator tools"
  homepage "https://github.com/SourceOS-Linux/sourceos-devtools"
  head "https://github.com/SourceOS-Linux/sourceos-devtools.git", branch: "main"

  depends_on "python@3.12"

  def install
    libexec.install Dir["*"]
    bin.write_exec_script libexec/"bin/sourceosctl"
    bin.write_exec_script libexec/"bin/sourceos-portable-ai"
  end

  def caveats
    <<~EOS
      Portable AI Kit surfaces:
        sourceosctl portable-ai profiles
        sourceos-portable-ai profiles

      Expected smoke marker:
        PortableAIProfiles

      This formula is a packaging scaffold. Runtime activation and policy gates remain in source repositories.
    EOS
  end
end
