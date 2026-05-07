# frozen_string_literal: true

class SourceosDevtools < Formula
  desc "SourceOS developer and Portable AI Kit operator tools"
  homepage "https://github.com/SourceOS-Linux/sourceos-devtools"
  head "https://github.com/SourceOS-Linux/sourceos-devtools.git", branch: "main"

  depends_on "python@3.12"

  def install
    libexec.install Dir["*"]

    chmod 0755, libexec/"bin/sourceosctl"
    chmod 0755, libexec/"bin/sourceos-portable-ai"

    (bin/"sourceosctl").write_env_script libexec/"bin/sourceosctl", {
      PATH: "#{Formula["python@3.12"].opt_bin}:$PATH",
      PYTHONPATH: libexec,
    }

    (bin/"sourceos-portable-ai").write_env_script libexec/"bin/sourceos-portable-ai", {
      PATH: "#{Formula["python@3.12"].opt_bin}:$PATH",
      PYTHONPATH: libexec,
    }
  end

  test do
    assert_match "PortableAIProfiles", shell_output("#{bin}/sourceosctl portable-ai profiles")
    assert_match "PortableAIProfiles", shell_output("#{bin}/sourceos-portable-ai profiles")
  end
end
